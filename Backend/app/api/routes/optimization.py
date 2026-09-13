"""RailSync 2.0 — Optimization, What-If, Pareto, Robustness, and Contingency Endpoints."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.optimization import (
    OptimizeRequest,
    OptimizeResponse,
    WhatIfRequest,
    WhatIfResponse,
    ParetoResponse,
    RobustnessResponse,
    PlanBResponse,
)
from app.services import optimization_service, whatif_service

router = APIRouter(tags=["Optimization"])


@router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Generate Optimal Maintenance Schedule",
    description=(
        "Executes the full CP-SAT optimization pipeline:\n"
        "1. Ingests pending tasks from database\n"
        "2. Loads trained Layer 1 ML failure forecasts and survival curves\n"
        "3. Executes Layer 2 multi-department negotiation and evidence scoring\n"
        "4. Enforces hard passenger train zero-conflict constraints and duration limits\n"
        "5. Optimizes soft freight penalties and block consolidations under selected policy"
    ),
)
def optimize(request: OptimizeRequest, db: Session = Depends(get_db)):
    try:
        result = optimization_service.run_optimization(
            db=db,
            policy=request.policy,
            horizon=request.horizon,
            objective_weights=request.objective_weights,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {type(e).__name__}",
        )

    if not result.feasible:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": result.status,
                "reason": result.error_message,
                "affected_tasks": result.affected_tasks,
            },
        )

    return result


@router.get(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Run Optimization (GET Convenience)",
    description="Convenience GET endpoint to trigger or retrieve optimization under a specified policy preset.",
)
def optimize_get(
    policy: str = Query(default="balanced", description="Policy preset: safety_first, balanced, throughput_first"),
    horizon: str = Query(default="both", description="Planning horizon: weekly, monthly, both"),
    db: Session = Depends(get_db),
):
    req = OptimizeRequest(policy=policy, horizon=horizon)
    return optimize(request=req, db=db)


@router.post(
    "/optimize/whatif",
    response_model=WhatIfResponse,
    summary="What-If Emergency Disruption Simulation",
    description=(
        "Simulates operational disruptions (rail fractures, OHE breakdown, block cancellations) "
        "and performs sub-second CP-SAT re-optimization (< 5.0s).\n"
        "Enforces chronological consistency: emergencies occurring at event_time are never assigned to elapsed past blocks."
    ),
)
@router.post("/what-if", response_model=WhatIfResponse, include_in_schema=False)
@router.post("/whatif", response_model=WhatIfResponse, include_in_schema=False)
def whatif(request: WhatIfRequest, db: Session = Depends(get_db)):
    try:
        return whatif_service.run_whatif(db, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"What-if simulation failed: {type(e).__name__}: {str(e)}",
        )


@router.get(
    "/optimize/weekly",
    summary="7-Day Tactical Weekly Plan",
    description="Generates a tactical 7-day railway maintenance possession schedule.",
)
@router.post("/optimize/weekly", include_in_schema=False)
def weekly_plan(
    policy: str = Query(default="balanced", description="Policy preset: safety_first, balanced, throughput_first"),
    db: Session = Depends(get_db),
):
    try:
        return optimization_service.run_weekly_planning(db=db, policy=policy)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Weekly plan generation failed: {type(e).__name__}: {str(e)}",
        )


@router.get(
    "/optimize/monthly",
    summary="30-Day Master Strategic Monthly Plan",
    description="Generates a master strategic 30-day corridor maintenance plan with ML expected downtime estimates.",
)
@router.post("/optimize/monthly", include_in_schema=False)
def monthly_plan(
    policy: str = Query(default="balanced", description="Policy preset: safety_first, balanced, throughput_first"),
    db: Session = Depends(get_db),
):
    try:
        return optimization_service.run_monthly_planning(db=db, policy=policy)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Monthly plan generation failed: {type(e).__name__}: {str(e)}",
        )


@router.get(
    "/optimize/pareto",
    response_model=ParetoResponse,
    summary="Multi-Policy Pareto Comparison",
    description="Evaluates the corridor schedule across Safety-First, Balanced, and Throughput-First policies, returning comparative trade-offs.",
)
@router.get("/optimize/policies", response_model=ParetoResponse, include_in_schema=False)
@router.post("/optimize/pareto", response_model=ParetoResponse, include_in_schema=False)
def pareto_frontier(db: Session = Depends(get_db)):
    try:
        return optimization_service.run_pareto(db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pareto frontier calculation failed: {type(e).__name__}: {str(e)}",
        )


@router.get(
    "/optimize/robustness",
    response_model=RobustnessResponse,
    summary="Monte Carlo Scenario Robustness Evaluation",
    description="Evaluates N=50 failure scenarios sampled from empirical Layer 1 survival curves S(t) to assess maintenance timeliness.",
)
@router.post("/optimize/robustness", response_model=RobustnessResponse, include_in_schema=False)
def scenario_robustness(
    num_scenarios: int = Query(default=50, description="Number of Monte Carlo failure scenarios to sample (e.g. 50)"),
    db: Session = Depends(get_db),
):
    try:
        return optimization_service.run_robustness(db=db, num_scenarios=num_scenarios)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario robustness evaluation failed: {type(e).__name__}: {str(e)}",
        )


@router.get(
    "/optimize/plan-b",
    response_model=PlanBResponse,
    summary="Top-5 Pre-Computed Plan-B Contingency Repository",
    description="Pre-computes and retrieves ready-to-dispatch contingency fallback plans for the Top-5 Indian Railways disruption scenarios.",
)
@router.get("/optimize/contingencies", response_model=PlanBResponse, include_in_schema=False)
@router.post("/optimize/plan-b", response_model=PlanBResponse, include_in_schema=False)
def plan_b_contingencies(db: Session = Depends(get_db)):
    try:
        return optimization_service.run_plan_b(db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan B contingencies generation failed: {type(e).__name__}: {str(e)}",
        )

