"""RailSync 2.0 — Plan response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.optimization import AssignmentOut


class PlanResponse(BaseModel):
    plan_id: str
    plan_type: str
    policy: str
    status: str
    is_current: bool
    optimization_run_id: str
    created_at: Optional[datetime] = None
    assignments: list[AssignmentOut] = []
    objective_values: Optional[dict[str, float]] = None
    robustness_score: Optional[float] = None
    execution_time_ms: Optional[int] = None
    total_assignments: int = 0

    model_config = {"from_attributes": True}


class ExplanationMetadata(BaseModel):
    primary_reason: str
    factors: list[dict[str, Any]] = []
    constraints: list[str] = []
    consolidation_benefit: Optional[str] = None
