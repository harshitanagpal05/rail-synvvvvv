"""RailSync 2.0 — Optimization service (the MAIN orchestrator).

Full pipeline: tasks → Layer 1 → Layer 2 → Layer 3 → DB → response.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db import repositories as repo
from app.integrations import layer2, layer3
from app.schemas.optimization import AssignmentOut, OptimizeResponse
from app.services import risk_service, task_service
from railsync.layer0.real_timetable import generate_real_timetable

log = get_logger("service.optimization")


def run_optimization(
    db: Session,
    policy: str = "balanced",
    horizon: str = "both",
    objective_weights: dict[str, float] | None = None,
) -> OptimizeResponse:
    """Execute the full optimization pipeline.

    1. Load pending tasks
    2. Load Layer 1 risk data
    3. Run Layer 2 negotiation
    4. Load timetable
    5. Run Layer 3 CP-SAT optimizer
    6. Persist run + plan + assignments
    7. Return structured result
    """
    pipeline_start = time.perf_counter()

    # 1. Load tasks
    tasks = task_service.get_pending_tasks(db)
    if not tasks:
        raise ValueError("No pending tasks to optimize. Submit tasks first via POST /ingest/tasks")

    # 2. Risk data
    risk_data = risk_service.get_risk_data_map(db)

    # 3. Negotiation
    neg_result = layer2.negotiate(tasks, risk_data)
    scored_tasks = neg_result["scored_tasks"]

    # Persist negotiation
    for scored in scored_tasks:
        repo.save_negotiation_result(db, **{
            "task_id": scored["task_id"],
            "evidence_score": scored["evidence_score"],
            "inflated_claim": scored["inflated_claim"],
            "weighted_priority": scored["weighted_priority"],
            "consolidation_group": scored.get("consolidation_group"),
            "negotiation_run_id": neg_result["negotiation_run_id"],
        })

    # 4. Timetable (from Layer 0 synthetic for prototype)
    timetable = generate_real_timetable()

    # 5 & 6. Run optimizer for requested horizons
    horizons_to_run = []
    if horizon in ("weekly", "both"):
        horizons_to_run.append(("weekly", 7))
    if horizon in ("monthly", "both"):
        horizons_to_run.append(("monthly", 30))

    all_assignments: list[dict[str, Any]] = []
    weekly_plan_data = None
    monthly_plan_data = None
    final_run_id = ""
    final_status = "optimal"
    final_feasible = True
    final_obj = {}
    final_robustness = None
    final_exec_ms = 0
    error_msg = None
    affected = []

    for plan_type, days in horizons_to_run:
        opt_result = layer3.optimize(
            tasks=scored_tasks,
            risk_data=risk_data,
            timetable=timetable,
            policy=policy,
            horizon_days=days,
        )
        final_run_id = opt_result["run_id"]
        final_exec_ms = opt_result["execution_time_ms"]

        if not opt_result["feasible"]:
            final_status = opt_result["status"]
            final_feasible = False
            error_msg = opt_result.get("error_message")
            affected = opt_result.get("affected_tasks", [])
            break

        # Persist optimization run
        repo.save_optimization_run(db, **{
            "run_id": opt_result["run_id"],
            "policy": policy,
            "horizon": plan_type,
            "status": opt_result["status"],
            "execution_time_ms": opt_result["execution_time_ms"],
            "objective_values": opt_result.get("objective_values"),
            "robustness_score": opt_result.get("robustness_score"),
            "input_summary": {
                "task_count": len(scored_tasks),
                "horizon_days": days,
                "policy": policy,
            },
            "output_summary": {
                "assignments": len(opt_result["assignments"]),
                "feasible": True,
            },
        })

        # Create plan
        plan_id = f"PLAN-{plan_type.upper()}-{uuid.uuid4().hex[:8].upper()}"
        repo.clear_current_plans(db, plan_type=plan_type)
        repo.save_block_plan(db, **{
            "plan_id": plan_id,
            "optimization_run_id": opt_result["run_id"],
            "plan_type": plan_type,
            "policy": policy,
            "status": "active",
            "is_current": True,
        })

        # Create assignments
        for a in opt_result["assignments"]:
            saved = repo.save_assignment(db, **{
                "plan_id": plan_id,
                "task_id": a["task_id"],
                "segment_id": a["segment_id"],
                "department": a["department"],
                "block_start": a["block_start"],
                "block_end": a["block_end"],
                "duration_hrs": a["duration_hrs"],
                "priority": a.get("priority"),
                "risk_30d": a.get("risk_30d"),
                "reason": a.get("reason"),
                "explanation": a.get("explanation"),
                "constraint_summary": a.get("constraint_summary"),
                "consolidation_group": a.get("consolidation_group"),
            })
            a["id"] = saved.id
            all_assignments.append(a)

        plan_summary = {
            "plan_id": plan_id,
            "plan_type": plan_type,
            "assignments": len(opt_result["assignments"]),
            "policy": policy,
        }
        if plan_type == "weekly":
            weekly_plan_data = plan_summary
        else:
            monthly_plan_data = plan_summary

        final_obj = opt_result.get("objective_values", {})
        final_robustness = opt_result.get("robustness_score")

    db.commit()
    total_ms = int((time.perf_counter() - pipeline_start) * 1000)

    log.info(
        "Full optimization pipeline complete run_id=%s policy=%s assignments=%d total_ms=%d",
        final_run_id, policy, len(all_assignments), total_ms,
    )

    return OptimizeResponse(
        run_id=final_run_id,
        policy=policy,
        horizon=horizon,
        status=final_status,
        feasible=final_feasible,
        execution_time_ms=total_ms,
        weekly_plan=weekly_plan_data,
        monthly_plan=monthly_plan_data,
        assignments=[AssignmentOut(**a) for a in all_assignments],
        objective_values=final_obj,
        robustness_score=final_robustness,
        total_assignments=len(all_assignments),
        error_message=error_msg,
        affected_tasks=affected,
        solver_status=final_status.upper(),
    )


def run_weekly_planning(db: Session, policy: str = "balanced") -> dict[str, Any]:
    """Generates a 7-day tactical weekly plan directly via Layer 3 generate_weekly_plan()."""
    tasks = task_service.get_pending_tasks(db)
    if not tasks:
        raise ValueError("No pending tasks to optimize.")
    risk_data = risk_service.get_risk_data_map(db)
    timetable = generate_real_timetable()
    result = layer3.run_weekly_plan(tasks=tasks, risk_data=risk_data, timetable=timetable, policy=policy)
    return result.to_dict()


def run_monthly_planning(db: Session, policy: str = "balanced") -> dict[str, Any]:
    """Generates a 30-day master strategic monthly plan directly via Layer 3 generate_monthly_plan()."""
    tasks = task_service.get_pending_tasks(db)
    if not tasks:
        raise ValueError("No pending tasks to optimize.")
    risk_data = risk_service.get_risk_data_map(db)
    timetable = generate_real_timetable(days=30)
    result = layer3.run_monthly_plan(tasks=tasks, risk_data=risk_data, timetable=timetable, policy=policy)
    return result.to_dict()


def run_pareto(db: Session) -> dict[str, Any]:
    """Computes Pareto frontier across policies directly via Layer 3 compute_pareto_frontier()."""
    tasks = task_service.get_pending_tasks(db)
    if not tasks:
        raise ValueError("No pending tasks for Pareto frontier analysis.")
    risk_data = risk_service.get_risk_data_map(db)
    timetable = generate_real_timetable()
    result = layer3.run_pareto_frontier(tasks=tasks, risk_data=risk_data, timetable=timetable)
    return result.to_dict()


def run_robustness(db: Session, num_scenarios: int = 50) -> dict[str, Any]:
    """Evaluates N=50 failure scenarios directly via Layer 3 evaluate_scenario_robustness()."""
    tasks = task_service.get_pending_tasks(db)
    if not tasks:
        raise ValueError("No pending tasks for robustness evaluation.")
    risk_data = risk_service.get_risk_data_map(db)
    timetable = generate_real_timetable()
    result = layer3.run_scenario_robustness(
        tasks=tasks, risk_data=risk_data, timetable=timetable, num_scenarios=num_scenarios
    )
    return result.to_dict()


def run_plan_b(db: Session) -> dict[str, Any]:
    """Pre-computes top disruption fallback plans directly via Layer 3 generate_plan_b_contingencies()."""
    tasks = task_service.get_pending_tasks(db)
    if not tasks:
        raise ValueError("No pending tasks for Plan B generation.")
    risk_data = risk_service.get_risk_data_map(db)
    timetable = generate_real_timetable()
    result = layer3.run_plan_b_contingencies(tasks=tasks, risk_data=risk_data, timetable=timetable)
    return result.to_dict()

