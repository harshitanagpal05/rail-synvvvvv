"""RailSync 2.0 — Feedback service (planned vs actual, metrics, recalibration hook)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db import repositories as repo
from app.schemas.feedback import (
    FeedbackCreateRequest,
    FeedbackMetricsResponse,
    FeedbackResponse,
)

log = get_logger("service.feedback")


def record_feedback(db: Session, request: FeedbackCreateRequest) -> FeedbackResponse:
    """Record executed block feedback and compute overrun."""
    assignment = repo.get_assignment_by_id(db, request.assignment_id)
    if assignment is None:
        raise ValueError(f"Assignment {request.assignment_id} not found")

    planned_start = request.planned_start or assignment.block_start
    planned_duration = request.planned_duration_hrs or assignment.duration_hrs

    overrun = None
    if request.actual_duration_hrs is not None:
        overrun = round(request.actual_duration_hrs - planned_duration, 2)

    feedback = repo.save_feedback(db, **{
        "assignment_id": request.assignment_id,
        "planned_start": planned_start,
        "planned_duration_hrs": planned_duration,
        "actual_start": request.actual_start,
        "actual_duration_hrs": request.actual_duration_hrs,
        "overrun_hrs": overrun,
        "overrun_cause": request.overrun_cause,
        "completion_status": request.completion_status,
        "notes": request.notes,
    })
    db.commit()

    log.info("Feedback recorded assignment_id=%d overrun=%.2f status=%s",
             request.assignment_id, overrun or 0, request.completion_status)

    return FeedbackResponse.model_validate(feedback)


def compute_metrics(db: Session) -> FeedbackMetricsResponse:
    """Calculate feedback metrics from all recorded feedback."""
    records = repo.get_all_feedback(db)
    total = len(records)

    if total == 0:
        return FeedbackMetricsResponse(
            total_executed_blocks=0,
            trend="insufficient_data",
            message="No executed blocks recorded yet. Submit feedback via POST /feedback/block",
        )

    planned_durations = [r.planned_duration_hrs for r in records]
    actual_durations = [r.actual_duration_hrs for r in records if r.actual_duration_hrs is not None]

    avg_planned = sum(planned_durations) / len(planned_durations)

    if not actual_durations:
        return FeedbackMetricsResponse(
            total_executed_blocks=total,
            average_planned_duration=round(avg_planned, 3),
            trend="insufficient_data",
            message="No actual durations recorded yet",
        )

    avg_actual = sum(actual_durations) / len(actual_durations)

    # Duration errors (actual - planned) where both exist
    errors = []
    for r in records:
        if r.actual_duration_hrs is not None:
            errors.append(r.actual_duration_hrs - r.planned_duration_hrs)

    avg_error = sum(errors) / len(errors) if errors else None
    avg_abs_error = sum(abs(e) for e in errors) / len(errors) if errors else None

    overrun_count = sum(1 for e in errors if e > 0)
    overrun_rate = overrun_count / len(errors) if errors else None

    # Trend: compare recent half vs previous half
    recent_error = None
    previous_error = None
    trend = "insufficient_data"

    if len(errors) >= 4:
        mid = len(errors) // 2
        # Records are ordered desc by created_at, so first half = recent
        recent_errors = errors[:mid]
        previous_errors = errors[mid:]
        recent_error = sum(abs(e) for e in recent_errors) / len(recent_errors)
        previous_error = sum(abs(e) for e in previous_errors) / len(previous_errors)

        if recent_error < previous_error * 0.9:
            trend = "improving"
        elif recent_error > previous_error * 1.1:
            trend = "worsening"
        else:
            trend = "stable"

    return FeedbackMetricsResponse(
        total_executed_blocks=total,
        average_planned_duration=round(avg_planned, 3),
        average_actual_duration=round(avg_actual, 3),
        average_duration_error=round(avg_error, 3) if avg_error is not None else None,
        average_absolute_duration_error=round(avg_abs_error, 3) if avg_abs_error is not None else None,
        overrun_rate=round(overrun_rate, 3) if overrun_rate is not None else None,
        recent_error=round(recent_error, 3) if recent_error is not None else None,
        previous_error=round(previous_error, 3) if previous_error is not None else None,
        trend=trend,
    )


def get_recalibration_dataset(db: Session) -> list[dict]:
    """Export feedback data for model recalibration (Layer 1 monthly recalibration hook)."""
    records = repo.get_all_feedback(db)
    return [
        {
            "assignment_id": r.assignment_id,
            "planned_duration_hrs": r.planned_duration_hrs,
            "actual_duration_hrs": r.actual_duration_hrs,
            "overrun_hrs": r.overrun_hrs,
            "overrun_cause": r.overrun_cause,
            "completion_status": r.completion_status,
        }
        for r in records
        if r.actual_duration_hrs is not None
    ]
