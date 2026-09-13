"""RailSync 2.0 — Plan retrieval service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db import repositories as repo
from app.schemas.optimization import AssignmentOut
from app.schemas.plans import PlanResponse

log = get_logger("service.plan")


def get_current_plan(db: Session) -> PlanResponse | None:
    """Get the latest current plan with assignments and run metadata."""
    plan = repo.get_current_plan(db)
    if plan is None:
        return None

    return _build_plan_response(db, plan)


def get_plan_by_id(db: Session, plan_id: str) -> PlanResponse | None:
    plan = repo.get_plan_by_id(db, plan_id)
    if plan is None:
        return None

    return _build_plan_response(db, plan)


def _build_plan_response(db: Session, plan) -> PlanResponse:
    assignments = repo.get_assignments_for_plan(db, plan.plan_id)
    run = repo.get_optimization_run(db, plan.optimization_run_id)

    return PlanResponse(
        plan_id=plan.plan_id,
        plan_type=plan.plan_type,
        policy=plan.policy,
        status=plan.status,
        is_current=plan.is_current,
        optimization_run_id=plan.optimization_run_id,
        created_at=plan.created_at,
        assignments=[
            AssignmentOut(
                id=a.id,
                task_id=a.task_id,
                segment_id=a.segment_id,
                department=a.department,
                block_start=a.block_start,
                block_end=a.block_end,
                duration_hrs=a.duration_hrs,
                priority=a.priority,
                risk_30d=a.risk_30d,
                reason=a.reason,
                explanation=a.explanation,
                consolidation_group=a.consolidation_group,
            )
            for a in assignments
        ],
        objective_values=run.objective_values if run else None,
        robustness_score=run.robustness_score if run else None,
        execution_time_ms=run.execution_time_ms if run else None,
        total_assignments=len(assignments),
    )
