"""RailSync 2.0 — Negotiation schemas (Layer 2 contract)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ScoredTask(BaseModel):
    task_id: str
    segment_id: str
    department: str
    claimed_criticality: int
    evidence_score: float
    inflated_claim: bool
    weighted_priority: float
    consolidation_group: Optional[str] = None


class NegotiationResponse(BaseModel):
    negotiation_run_id: str
    scored_tasks: list[ScoredTask]
    total_tasks: int
    inflated_count: int
    consolidation_groups: int
    conflicts: list[str] = []
