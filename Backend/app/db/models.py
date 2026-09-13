"""RailSync 2.0 — SQLAlchemy ORM models.

Eight tables with real foreign-key relationships:
  segments → maintenance_tasks → negotiation_results
                               → block_assignments → feedback_records
  optimization_runs → block_plans → block_assignments
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


# ── 1. Segments ──────────────────────────────────────────────

class Segment(Base):
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(String(64), unique=True, nullable=False, index=True)
    division = Column(String(64), nullable=False)
    section = Column(String(128), nullable=True)
    asset_type = Column(String(32), nullable=False)  # TRACK, OHE, BRIDGE, SIGNAL
    length_km = Column(Float, nullable=False)
    age_years = Column(Float, nullable=False)
    installation_year = Column(Integer, nullable=True)
    curve_gradient_class = Column(String(16), nullable=False, default="flat")
    monsoon_exposure = Column(String(16), nullable=False, default="low")
    freight_density_class = Column(String(16), nullable=False, default="medium")
    corridor = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    tasks = relationship("MaintenanceTask", back_populates="segment")
    risk_predictions = relationship("RiskPrediction", back_populates="segment")


# ── 2. Maintenance Tasks ─────────────────────────────────────

class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), unique=True, nullable=False, index=True)
    segment_id = Column(String(64), ForeignKey("segments.segment_id"), nullable=False)
    department = Column(String(16), nullable=False)  # TRACK, OHE, SIG, TELE, BRIDGE
    task_type = Column(String(64), nullable=False)
    claimed_criticality = Column(Integer, nullable=False)  # 1-5
    min_duration_hrs = Column(Float, nullable=False)
    preferred_window_start = Column(DateTime, nullable=True)
    preferred_window_end = Column(DateTime, nullable=True)
    planned_duration_hrs = Column(Float, nullable=True)
    actual_duration_hrs = Column(Float, nullable=True)
    overdue = Column(Boolean, default=False)
    status = Column(String(24), default="pending")  # pending, scheduled, completed, cancelled
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    segment = relationship("Segment", back_populates="tasks")
    negotiation_results = relationship("NegotiationResult", back_populates="task")
    assignments = relationship("BlockAssignment", back_populates="task")


# ── 3. Risk Predictions (Layer 1 output) ─────────────────────

class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(String(64), ForeignKey("segments.segment_id"), nullable=False)
    risk_30d = Column(Float, nullable=False)
    expected_downtime_days = Column(Float, nullable=False)
    preventive_block_duration_hrs = Column(Float, nullable=False)
    confidence = Column(String(16), nullable=False)  # high, medium, low
    overrun_probability = Column(Float, nullable=True)
    cold_start_fallback = Column(Boolean, nullable=True, default=False)
    survival_curve = Column(JSONB, nullable=True)
    feature_contributions = Column(JSONB, nullable=True)
    model_version = Column(String(32), nullable=True)
    prediction_timestamp = Column(DateTime, server_default=func.now())

    segment = relationship("Segment", back_populates="risk_predictions")

    __table_args__ = (
        Index("ix_risk_segment_ts", "segment_id", "prediction_timestamp"),
    )


# ── 4. Negotiation Results (Layer 2 output) ──────────────────

class NegotiationResult(Base):
    __tablename__ = "negotiation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("maintenance_tasks.task_id"), nullable=False)
    evidence_score = Column(Float, nullable=False)
    inflated_claim = Column(Boolean, default=False)
    weighted_priority = Column(Float, nullable=False)
    consolidation_group = Column(String(64), nullable=True)
    negotiation_run_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    task = relationship("MaintenanceTask", back_populates="negotiation_results")


# ── 5. Optimization Runs ─────────────────────────────────────

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    policy = Column(String(24), nullable=False)
    horizon = Column(String(16), nullable=False)
    status = Column(String(24), nullable=False)  # running, optimal, feasible, infeasible, error
    execution_time_ms = Column(Integer, nullable=True)
    objective_values = Column(JSONB, nullable=True)
    robustness_score = Column(Float, nullable=True)
    input_summary = Column(JSONB, nullable=True)
    output_summary = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    plans = relationship("BlockPlan", back_populates="optimization_run")


# ── 6. Block Plans ────────────────────────────────────────────

class BlockPlan(Base):
    __tablename__ = "block_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(String(64), unique=True, nullable=False, index=True)
    optimization_run_id = Column(String(64), ForeignKey("optimization_runs.run_id"), nullable=False)
    plan_type = Column(String(16), nullable=False)  # weekly, monthly, what_if
    policy = Column(String(24), nullable=False)
    status = Column(String(24), default="active")
    is_current = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    optimization_run = relationship("OptimizationRun", back_populates="plans")
    assignments = relationship("BlockAssignment", back_populates="plan")


# ── 7. Block Assignments ─────────────────────────────────────

class BlockAssignment(Base):
    __tablename__ = "block_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(String(64), ForeignKey("block_plans.plan_id"), nullable=False)
    task_id = Column(String(64), ForeignKey("maintenance_tasks.task_id"), nullable=False)
    segment_id = Column(String(64), nullable=False)
    department = Column(String(16), nullable=False)
    block_start = Column(DateTime, nullable=False)
    block_end = Column(DateTime, nullable=False)
    duration_hrs = Column(Float, nullable=False)
    priority = Column(Float, nullable=True)
    risk_30d = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    explanation = Column(JSONB, nullable=True)  # full why-metadata
    constraint_summary = Column(JSONB, nullable=True)
    consolidation_group = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    plan = relationship("BlockPlan", back_populates="assignments")
    task = relationship("MaintenanceTask", back_populates="assignments")
    feedback = relationship("FeedbackRecord", back_populates="assignment", uselist=False)


# ── 8. Feedback Records ──────────────────────────────────────

class FeedbackRecord(Base):
    __tablename__ = "feedback_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("block_assignments.id"), nullable=False, unique=True)
    planned_start = Column(DateTime, nullable=False)
    planned_duration_hrs = Column(Float, nullable=False)
    actual_start = Column(DateTime, nullable=True)
    actual_duration_hrs = Column(Float, nullable=True)
    overrun_hrs = Column(Float, nullable=True)
    overrun_cause = Column(String(128), nullable=True)
    completion_status = Column(String(24), nullable=False)  # completed, partial, cancelled, overrun
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    assignment = relationship("BlockAssignment", back_populates="feedback")
