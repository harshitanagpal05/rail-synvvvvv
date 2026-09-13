"""Initial RailSync 2.0 schema — 8 tables with FK relationships.

Revision ID: 001_initial
Revises: None
Create Date: 2026-09-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Segments
    op.create_table(
        "segments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("segment_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("division", sa.String(64), nullable=False),
        sa.Column("section", sa.String(128), nullable=True),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("length_km", sa.Float, nullable=False),
        sa.Column("age_years", sa.Float, nullable=False),
        sa.Column("installation_year", sa.Integer, nullable=True),
        sa.Column("curve_gradient_class", sa.String(16), nullable=False, server_default="flat"),
        sa.Column("monsoon_exposure", sa.String(16), nullable=False, server_default="low"),
        sa.Column("freight_density_class", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("corridor", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 2. Maintenance Tasks
    op.create_table(
        "maintenance_tasks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("segment_id", sa.String(64), sa.ForeignKey("segments.segment_id"), nullable=False),
        sa.Column("department", sa.String(16), nullable=False),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("claimed_criticality", sa.Integer, nullable=False),
        sa.Column("min_duration_hrs", sa.Float, nullable=False),
        sa.Column("preferred_window_start", sa.DateTime, nullable=True),
        sa.Column("preferred_window_end", sa.DateTime, nullable=True),
        sa.Column("planned_duration_hrs", sa.Float, nullable=True),
        sa.Column("actual_duration_hrs", sa.Float, nullable=True),
        sa.Column("overdue", sa.Boolean, default=False),
        sa.Column("status", sa.String(24), default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 3. Risk Predictions
    op.create_table(
        "risk_predictions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("segment_id", sa.String(64), sa.ForeignKey("segments.segment_id"), nullable=False),
        sa.Column("risk_30d", sa.Float, nullable=False),
        sa.Column("expected_downtime_days", sa.Float, nullable=False),
        sa.Column("preventive_block_duration_hrs", sa.Float, nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("survival_curve", postgresql.JSONB, nullable=True),
        sa.Column("feature_contributions", postgresql.JSONB, nullable=True),
        sa.Column("model_version", sa.String(32), nullable=True),
        sa.Column("prediction_timestamp", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_risk_segment_ts", "risk_predictions", ["segment_id", "prediction_timestamp"])

    # 4. Negotiation Results
    op.create_table(
        "negotiation_results",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("maintenance_tasks.task_id"), nullable=False),
        sa.Column("evidence_score", sa.Float, nullable=False),
        sa.Column("inflated_claim", sa.Boolean, default=False),
        sa.Column("weighted_priority", sa.Float, nullable=False),
        sa.Column("consolidation_group", sa.String(64), nullable=True),
        sa.Column("negotiation_run_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 5. Optimization Runs
    op.create_table(
        "optimization_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("policy", sa.String(24), nullable=False),
        sa.Column("horizon", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("execution_time_ms", sa.Integer, nullable=True),
        sa.Column("objective_values", postgresql.JSONB, nullable=True),
        sa.Column("robustness_score", sa.Float, nullable=True),
        sa.Column("input_summary", postgresql.JSONB, nullable=True),
        sa.Column("output_summary", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 6. Block Plans
    op.create_table(
        "block_plans",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("optimization_run_id", sa.String(64), sa.ForeignKey("optimization_runs.run_id"), nullable=False),
        sa.Column("plan_type", sa.String(16), nullable=False),
        sa.Column("policy", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), default="active"),
        sa.Column("is_current", sa.Boolean, default=False, index=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 7. Block Assignments
    op.create_table(
        "block_assignments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.String(64), sa.ForeignKey("block_plans.plan_id"), nullable=False),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("maintenance_tasks.task_id"), nullable=False),
        sa.Column("segment_id", sa.String(64), nullable=False),
        sa.Column("department", sa.String(16), nullable=False),
        sa.Column("block_start", sa.DateTime, nullable=False),
        sa.Column("block_end", sa.DateTime, nullable=False),
        sa.Column("duration_hrs", sa.Float, nullable=False),
        sa.Column("priority", sa.Float, nullable=True),
        sa.Column("risk_30d", sa.Float, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("explanation", postgresql.JSONB, nullable=True),
        sa.Column("constraint_summary", postgresql.JSONB, nullable=True),
        sa.Column("consolidation_group", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # 8. Feedback Records
    op.create_table(
        "feedback_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("assignment_id", sa.Integer, sa.ForeignKey("block_assignments.id"), nullable=False, unique=True),
        sa.Column("planned_start", sa.DateTime, nullable=False),
        sa.Column("planned_duration_hrs", sa.Float, nullable=False),
        sa.Column("actual_start", sa.DateTime, nullable=True),
        sa.Column("actual_duration_hrs", sa.Float, nullable=True),
        sa.Column("overrun_hrs", sa.Float, nullable=True),
        sa.Column("overrun_cause", sa.String(128), nullable=True),
        sa.Column("completion_status", sa.String(24), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("feedback_records")
    op.drop_table("block_assignments")
    op.drop_table("block_plans")
    op.drop_table("optimization_runs")
    op.drop_table("negotiation_results")
    op.drop_table("risk_predictions")
    op.drop_table("maintenance_tasks")
    op.drop_table("segments")
