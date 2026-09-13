"""RailSync 2.0 — Risk prediction schemas (Layer 1 output contract)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class FeatureContribution(BaseModel):
    name: str
    importance: Optional[float] = None
    value: Optional[float] = None
    contribution: Optional[float] = None


class SurvivalPoint(BaseModel):
    day: int
    survival_probability: float
    daily_hazard: Optional[float] = None
    cumulative_failure_probability: Optional[float] = None


class RiskPredictionResponse(BaseModel):
    segment_id: str
    risk_30d: float
    expected_downtime_days: float
    preventive_block_duration_hrs: float
    confidence: str
    overrun_probability: Optional[float] = None
    cold_start_fallback: Optional[bool] = None
    survival_curve: list[SurvivalPoint] = []
    feature_contributions: list[FeatureContribution] = []
    model_version: Optional[str] = None
    prediction_timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SegmentRiskSummary(BaseModel):
    segment_id: str
    division: Optional[str] = None
    corridor: Optional[str] = None
    risk_30d: float
    expected_downtime_days: float
    preventive_block_duration_hrs: float
    confidence: str
    overrun_probability: Optional[float] = None
    cold_start_fallback: Optional[bool] = None
