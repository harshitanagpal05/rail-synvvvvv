"""RailSync 2.0 — Optimization and what-if schemas (Layer 3 contract)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

VALID_POLICIES = {"safety_first", "balanced", "throughput_first"}
VALID_HORIZONS = {"weekly", "monthly", "both"}


class OptimizeRequest(BaseModel):
    policy: str = Field(default="balanced")
    horizon: str = Field(default="both")
    objective_weights: Optional[dict[str, float]] = None

    @field_validator("policy")
    @classmethod
    def validate_policy(cls, v):
        if v not in VALID_POLICIES:
            raise ValueError(f"policy must be one of {VALID_POLICIES}")
        return v

    @field_validator("horizon")
    @classmethod
    def validate_horizon(cls, v):
        if v not in VALID_HORIZONS:
            raise ValueError(f"horizon must be one of {VALID_HORIZONS}")
        return v


class WhatIfRequest(BaseModel):
    # Disruption scenario fields (Layer 3 contract)
    scenario_id: Optional[str] = None
    description: Optional[str] = None
    emergency_tasks: Optional[list[dict[str, Any]]] = None
    cancelled_blocks: Optional[list[str]] = None
    modified_passenger_conflicts: Optional[dict[str, dict[str, int]]] = None
    modified_block_durations: Optional[dict[str, float]] = None
    locked_assignments: Optional[dict[str, str]] = None

    # Event fields & Frontend aliases
    type: Optional[str] = Field(default=None, description="Disruption event type, e.g. RAIL_FRACTURE, OHE_BREAKDOWN")
    event_type: Optional[str] = Field(default=None, description="Alias for type")
    segment_id: Optional[str] = Field(default=None, description="Affected corridor segment, e.g. SEG-039")
    time: Optional[str] = Field(default=None, description="Event occurrence time, e.g. 11:30 or 2026-09-15 11:30")
    event_time: Optional[str] = Field(default=None, description="Alias for time")
    severity: Optional[str] = Field(default="moderate", description="Severity level: low, moderate, high, critical, emergency")


class AssignmentOut(BaseModel):
    id: Optional[int] = None
    task_id: str
    segment_id: str
    department: str
    block_start: datetime
    block_end: datetime
    duration_hrs: float
    priority: Optional[float] = None
    risk_30d: Optional[float] = None
    reason: Optional[str] = None
    explanation: Optional[dict[str, Any]] = None
    constraint_summary: Optional[dict[str, Any]] = None
    consolidation_group: Optional[str] = None
    status: str = Field(default="SCHEDULED", description="Assignment status: SCHEDULED, UNASSIGNED, RESCHEDULED")
    assigned_block: Optional[str] = Field(default=None, description="Assigned possession block window ID, e.g. BLK-D1-NIGHT")
    why: Optional[str] = Field(default=None, description="Human-readable explanation of why this block was selected")

    model_config = {"from_attributes": True}


class OptimizeResponse(BaseModel):
    run_id: str
    policy: str
    horizon: str
    status: str
    feasible: bool
    execution_time_ms: int
    weekly_plan: Optional[dict[str, Any]] = None
    monthly_plan: Optional[dict[str, Any]] = None
    assignments: list[AssignmentOut] = []
    objective_values: Optional[dict[str, float]] = None
    robustness_score: Optional[float] = None
    total_assignments: int = 0
    error_message: Optional[str] = None
    affected_tasks: list[str] = []
    solver_status: Optional[str] = None


class PlanDiff(BaseModel):
    task_id: str
    change_type: str  # added, removed, moved, modified, RESCHEDULED, NEWLY_SCHEDULED, DISPLACED_UNASSIGNED
    old_start: Optional[datetime] = None
    old_end: Optional[datetime] = None
    new_start: Optional[datetime] = None
    new_end: Optional[datetime] = None
    original_block: Optional[str] = None
    new_block: Optional[str] = None
    reason: str = ""


class WhatIfResponse(BaseModel):
    feasible: bool
    run_id: str
    scenario_id: Optional[str] = None
    plan_b: Optional[dict[str, Any]] = None
    changed_assignments: list[PlanDiff] = []
    added_assignments: list[AssignmentOut] = []
    removed_assignments: list[AssignmentOut] = []
    reason: list[str] = []
    execution_time_ms: int = 0
    objective_values: Optional[dict[str, float]] = None
    solver_status: Optional[str] = None
    summary: Optional[str] = None


class ParetoResponse(BaseModel):
    recommended_preset: str
    summary: str
    points: list[dict[str, Any]]


class RobustnessResponse(BaseModel):
    total_scenarios: int
    feasible_scenarios_count: int
    robustness_percentage: float
    total_simulated_failures: int
    failures_prevented_count: int
    failure_prevention_rate: float
    vulnerable_assets: list[str] = []
    summary: str = ""
    scenario_evaluations: list[dict[str, Any]] = []


class PlanBResponse(BaseModel):
    generated_at: str = ""
    baseline_metrics: dict[str, Any] = {}
    top_contingencies_count: int = 0
    contingencies: list[dict[str, Any]] = []
    total_contingencies: Optional[int] = None
    scenarios: Optional[list[dict[str, Any]]] = None
    summary: Optional[str] = None

