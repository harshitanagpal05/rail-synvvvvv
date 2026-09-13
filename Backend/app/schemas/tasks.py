"""RailSync 2.0 — Task schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

VALID_DEPARTMENTS = {"TRACK", "OHE", "SIG", "TELE", "BRIDGE"}


class PreferredWindow(BaseModel):
    start: datetime
    end: datetime

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v, info):
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("preferred_window.end must be after start")
        return v


class TaskCreateRequest(BaseModel):
    task_id: str = Field(..., min_length=1, max_length=64)
    segment_id: str = Field(..., min_length=1, max_length=64)
    department: str = Field(..., min_length=1, max_length=16)
    claimed_criticality: int = Field(..., ge=1, le=5)
    min_duration_hrs: float = Field(..., gt=0)
    preferred_window: Optional[PreferredWindow] = None
    task_type: str = Field(..., min_length=1, max_length=64)
    overdue: bool = False

    @field_validator("department")
    @classmethod
    def validate_department(cls, v):
        v_upper = v.upper()
        if v_upper not in VALID_DEPARTMENTS:
            raise ValueError(f"department must be one of {VALID_DEPARTMENTS}")
        return v_upper


class TaskResponse(BaseModel):
    task_id: str
    segment_id: str
    department: str
    task_type: str
    claimed_criticality: int
    min_duration_hrs: float
    preferred_window_start: Optional[datetime] = None
    preferred_window_end: Optional[datetime] = None
    overdue: bool
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
