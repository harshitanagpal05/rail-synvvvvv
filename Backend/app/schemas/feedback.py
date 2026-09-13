"""RailSync 2.0 — Feedback schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

VALID_STATUSES = {"completed", "partial", "cancelled", "overrun"}


class FeedbackCreateRequest(BaseModel):
    assignment_id: int
    planned_start: Optional[datetime] = None
    planned_duration_hrs: Optional[float] = Field(default=None, gt=0)
    actual_start: Optional[datetime] = None
    actual_duration_hrs: Optional[float] = Field(default=None, gt=0)
    completion_status: str
    overrun_cause: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("completion_status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_STATUSES:
            raise ValueError(f"completion_status must be one of {VALID_STATUSES}")
        return v


class FeedbackResponse(BaseModel):
    id: int
    assignment_id: int
    planned_start: datetime
    planned_duration_hrs: float
    actual_start: Optional[datetime] = None
    actual_duration_hrs: Optional[float] = None
    overrun_hrs: Optional[float] = None
    completion_status: str
    overrun_cause: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FeedbackMetricsResponse(BaseModel):
    total_executed_blocks: int
    average_planned_duration: Optional[float] = None
    average_actual_duration: Optional[float] = None
    average_duration_error: Optional[float] = None
    average_absolute_duration_error: Optional[float] = None
    overrun_rate: Optional[float] = None
    recent_error: Optional[float] = None
    previous_error: Optional[float] = None
    trend: Optional[str] = None  # improving, worsening, stable, insufficient_data
    message: Optional[str] = None
