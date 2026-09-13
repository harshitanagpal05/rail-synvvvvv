"""RailSync 2.0 — Negotiation service (Layer 2 orchestration)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db import repositories as repo
from app.integrations import layer2
from app.schemas.negotiation import NegotiationResponse, ScoredTask
from app.services import risk_service, task_service

log = get_logger("service.negotiation")


def run_negotiation(db: Session) -> NegotiationResponse:
    """Execute full negotiation: load tasks → get risk data → score → persist."""
    tasks = task_service.get_pending_tasks(db)
    if not tasks:
        raise ValueError("No pending tasks available for negotiation")

    risk_data = risk_service.get_risk_data_map(db)

    result = layer2.negotiate(tasks, risk_data)

    # Persist each scored result
    for scored in result["scored_tasks"]:
        repo.save_negotiation_result(db, **{
            "task_id": scored["task_id"],
            "evidence_score": scored["evidence_score"],
            "inflated_claim": scored["inflated_claim"],
            "weighted_priority": scored["weighted_priority"],
            "consolidation_group": scored.get("consolidation_group"),
            "negotiation_run_id": result["negotiation_run_id"],
        })

    db.commit()
    log.info("Negotiation persisted run_id=%s tasks=%d",
             result["negotiation_run_id"], len(result["scored_tasks"]))

    return NegotiationResponse(
        negotiation_run_id=result["negotiation_run_id"],
        scored_tasks=[ScoredTask(**s) for s in result["scored_tasks"]],
        total_tasks=result["total_tasks"],
        inflated_count=result["inflated_count"],
        consolidation_groups=result["consolidation_groups"],
        conflicts=result.get("conflicts", []),
    )
