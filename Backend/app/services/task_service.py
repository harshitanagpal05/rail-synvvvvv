"""RailSync 2.0 — Task ingestion service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db import repositories as repo
from app.schemas.tasks import TaskCreateRequest, TaskResponse

log = get_logger("service.task")


def ingest_task(db: Session, request: TaskCreateRequest) -> tuple[TaskResponse, bool]:
    """Validate and persist a maintenance task. Idempotent on task_id.

    Returns (response, created) where created=False means the task already existed and was updated.
    """
    segment = repo.get_segment(db, request.segment_id)
    if segment is None:
        raise ValueError(f"Segment {request.segment_id} does not exist")

    kwargs = {
        "task_id": request.task_id,
        "segment_id": request.segment_id,
        "department": request.department,
        "task_type": request.task_type,
        "claimed_criticality": request.claimed_criticality,
        "min_duration_hrs": request.min_duration_hrs,
        "overdue": request.overdue,
        "status": "pending",
    }
    if request.preferred_window:
        kwargs["preferred_window_start"] = request.preferred_window.start
        kwargs["preferred_window_end"] = request.preferred_window.end

    task, created = repo.upsert_task(db, **kwargs)
    db.commit()

    action = "ingested" if created else "updated"
    log.info("Task %s task_id=%s segment=%s", action, task.task_id, task.segment_id)

    return TaskResponse.model_validate(task), created


def get_all_tasks(db: Session) -> list[TaskResponse]:
    tasks = repo.get_all_tasks(db)
    return [TaskResponse.model_validate(t) for t in tasks]


def get_pending_tasks(db: Session) -> list[dict]:
    """Get pending tasks as dicts for Layer 2/3 consumption."""
    tasks = repo.get_tasks_by_status(db, "pending")
    return [
        {
            "task_id": t.task_id,
            "segment_id": t.segment_id,
            "department": t.department,
            "task_type": t.task_type,
            "claimed_criticality": t.claimed_criticality,
            "min_duration_hrs": t.min_duration_hrs,
            "overdue": t.overdue,
            "preferred_window_start": t.preferred_window_start,
            "preferred_window_end": t.preferred_window_end,
        }
        for t in tasks
    ]
