"""RailSync 2.0 — Data access repositories (thin CRUD layer, no business logic)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db.models import (
    BlockAssignment,
    BlockPlan,
    FeedbackRecord,
    MaintenanceTask,
    NegotiationResult,
    OptimizationRun,
    RiskPrediction,
    Segment,
)


# ── Segments ──────────────────────────────────────────────────

def get_segment(db: Session, segment_id: str) -> Optional[Segment]:
    return db.query(Segment).filter(Segment.segment_id == segment_id).first()


def get_all_segments(db: Session) -> list[Segment]:
    return db.query(Segment).order_by(Segment.segment_id).all()


def upsert_segment(db: Session, **kwargs) -> Segment:
    existing = get_segment(db, kwargs["segment_id"])
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        db.flush()
        return existing
    seg = Segment(**kwargs)
    db.add(seg)
    db.flush()
    return seg


# ── Maintenance Tasks ─────────────────────────────────────────

def get_task(db: Session, task_id: str) -> Optional[MaintenanceTask]:
    return db.query(MaintenanceTask).filter(MaintenanceTask.task_id == task_id).first()


def get_tasks_by_status(db: Session, status: str) -> list[MaintenanceTask]:
    return db.query(MaintenanceTask).filter(MaintenanceTask.status == status).all()


def get_all_tasks(db: Session) -> list[MaintenanceTask]:
    return db.query(MaintenanceTask).order_by(MaintenanceTask.created_at.desc()).all()


def upsert_task(db: Session, **kwargs) -> tuple[MaintenanceTask, bool]:
    """Returns (task, created). If task_id exists, updates it."""
    existing = get_task(db, kwargs["task_id"])
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        db.flush()
        return existing, False
    task = MaintenanceTask(**kwargs)
    db.add(task)
    db.flush()
    return task, True


# ── Risk Predictions ──────────────────────────────────────────

def get_latest_risk(db: Session, segment_id: str) -> Optional[RiskPrediction]:
    return (
        db.query(RiskPrediction)
        .filter(RiskPrediction.segment_id == segment_id)
        .order_by(desc(RiskPrediction.prediction_timestamp))
        .first()
    )


def get_all_latest_risks(db: Session) -> list[RiskPrediction]:
    """Latest risk prediction per segment via a subquery."""
    subq = (
        db.query(
            RiskPrediction.segment_id,
            func.max(RiskPrediction.prediction_timestamp).label("max_ts"),
        )
        .group_by(RiskPrediction.segment_id)
        .subquery()
    )
    return (
        db.query(RiskPrediction)
        .join(
            subq,
            (RiskPrediction.segment_id == subq.c.segment_id)
            & (RiskPrediction.prediction_timestamp == subq.c.max_ts),
        )
        .order_by(RiskPrediction.risk_30d.desc())
        .all()
    )


def save_risk_prediction(db: Session, **kwargs) -> RiskPrediction:
    pred = RiskPrediction(**kwargs)
    db.add(pred)
    db.flush()
    return pred


# ── Negotiation Results ───────────────────────────────────────

def save_negotiation_result(db: Session, **kwargs) -> NegotiationResult:
    result = NegotiationResult(**kwargs)
    db.add(result)
    db.flush()
    return result


def get_negotiation_by_run(db: Session, run_id: str) -> list[NegotiationResult]:
    return (
        db.query(NegotiationResult)
        .filter(NegotiationResult.negotiation_run_id == run_id)
        .all()
    )


# ── Optimization Runs ────────────────────────────────────────

def save_optimization_run(db: Session, **kwargs) -> OptimizationRun:
    run = OptimizationRun(**kwargs)
    db.add(run)
    db.flush()
    return run


def get_optimization_run(db: Session, run_id: str) -> Optional[OptimizationRun]:
    return db.query(OptimizationRun).filter(OptimizationRun.run_id == run_id).first()


# ── Block Plans ───────────────────────────────────────────────

def save_block_plan(db: Session, **kwargs) -> BlockPlan:
    plan = BlockPlan(**kwargs)
    db.add(plan)
    db.flush()
    return plan


def get_current_plan(db: Session, plan_type: Optional[str] = None) -> Optional[BlockPlan]:
    q = db.query(BlockPlan).filter(BlockPlan.is_current == True)
    if plan_type:
        q = q.filter(BlockPlan.plan_type == plan_type)
    return q.order_by(desc(BlockPlan.created_at)).first()


def get_plan_by_id(db: Session, plan_id: str) -> Optional[BlockPlan]:
    return db.query(BlockPlan).filter(BlockPlan.plan_id == plan_id).first()


def clear_current_plans(db: Session, plan_type: Optional[str] = None) -> None:
    """Unset is_current for existing plans of a given type."""
    q = db.query(BlockPlan).filter(BlockPlan.is_current == True)
    if plan_type:
        q = q.filter(BlockPlan.plan_type == plan_type)
    q.update({"is_current": False})
    db.flush()


# ── Block Assignments ─────────────────────────────────────────

def save_assignment(db: Session, **kwargs) -> BlockAssignment:
    a = BlockAssignment(**kwargs)
    db.add(a)
    db.flush()
    return a


def get_assignments_for_plan(db: Session, plan_id: str) -> list[BlockAssignment]:
    return (
        db.query(BlockAssignment)
        .filter(BlockAssignment.plan_id == plan_id)
        .order_by(BlockAssignment.block_start)
        .all()
    )


def get_assignment_by_id(db: Session, assignment_id: int) -> Optional[BlockAssignment]:
    return db.query(BlockAssignment).filter(BlockAssignment.id == assignment_id).first()


# ── Feedback Records ─────────────────────────────────────────

def save_feedback(db: Session, **kwargs) -> FeedbackRecord:
    rec = FeedbackRecord(**kwargs)
    db.add(rec)
    db.flush()
    return rec


def get_all_feedback(db: Session) -> list[FeedbackRecord]:
    return db.query(FeedbackRecord).order_by(desc(FeedbackRecord.created_at)).all()


def get_feedback_count(db: Session) -> int:
    return db.query(func.count(FeedbackRecord.id)).scalar() or 0
