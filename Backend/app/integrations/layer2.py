"""RailSync 2.0 — Layer 2 Integration Adapter: Department Negotiation.

Evidence-based scoring, inflated claim detection, weighted priority,
and task consolidation. Standalone implementation matching the Layer 2 contract.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.logging import get_logger

log = get_logger("layer2")

# Thresholds
_INFLATION_THRESHOLD = 1.5  # claimed/evidence ratio above which we flag


def _compute_evidence_score(
    claimed_criticality: int,
    risk_30d: float,
    overdue: bool,
) -> float:
    """Evidence score from 0–5 based on actual risk data, independent of department claim."""
    base = risk_30d * 5.0
    if overdue:
        base += 0.8
    return round(min(base, 5.0), 3)


def _detect_inflation(claimed: int, evidence: float) -> bool:
    if evidence < 0.5:
        return claimed >= 3
    return (claimed / evidence) > _INFLATION_THRESHOLD


def _weighted_priority(
    evidence_score: float,
    risk_30d: float,
    overdue: bool,
) -> float:
    """Weighted priority: 0.5×evidence + 0.3×risk_scaled + 0.2×overdue_flag."""
    overdue_val = 1.0 if overdue else 0.0
    priority = 0.5 * evidence_score + 0.3 * (risk_30d * 5.0) + 0.2 * (overdue_val * 5.0)
    return round(priority, 3)


def _consolidate_tasks(tasks: list[dict[str, Any]]) -> dict[str, str]:
    """Group tasks on the same segment that can share a block window.

    Returns mapping of task_id → consolidation_group_id.
    """
    groups: dict[str, list[str]] = {}
    for t in tasks:
        key = t.get("segment_id", "")
        groups.setdefault(key, []).append(t["task_id"])

    result: dict[str, str] = {}
    group_idx = 1
    for seg_id, task_ids in groups.items():
        if len(task_ids) > 1:
            group_name = f"CG-{group_idx:03d}"
            for tid in task_ids:
                result[tid] = group_name
            group_idx += 1
    return result


def negotiate(
    tasks: list[dict[str, Any]],
    risk_data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Run department negotiation on a task pool.

    Args:
        tasks: list of task dicts with task_id, segment_id, department,
               claimed_criticality, overdue, min_duration_hrs
        risk_data: mapping of segment_id → Layer 1 risk prediction dict

    Returns:
        Normalized negotiation result.
    """
    run_id = f"NEG-{uuid.uuid4().hex[:12].upper()}"
    log.info("Negotiation started run_id=%s tasks=%d", run_id, len(tasks))

    consolidation_map = _consolidate_tasks(tasks)
    scored: list[dict[str, Any]] = []
    conflicts: list[str] = []

    for task in tasks:
        seg_risk = risk_data.get(task["segment_id"], {})
        risk_30d = seg_risk.get("risk_30d", 0.0)

        evidence = _compute_evidence_score(
            claimed_criticality=task["claimed_criticality"],
            risk_30d=risk_30d,
            overdue=task.get("overdue", False),
        )

        inflated = _detect_inflation(task["claimed_criticality"], evidence)
        if inflated:
            conflicts.append(
                f"{task['task_id']}: {task['department']} claimed {task['claimed_criticality']}"
                f" but evidence supports {evidence:.1f}"
            )

        priority = _weighted_priority(
            evidence_score=evidence,
            risk_30d=risk_30d,
            overdue=task.get("overdue", False),
        )

        task_entry = dict(task)
        task_entry.update({
            "task_id": task["task_id"],
            "segment_id": task["segment_id"],
            "department": task["department"],
            "claimed_criticality": task["claimed_criticality"],
            "evidence_score": evidence,
            "inflated_claim": inflated,
            "weighted_priority": priority,
            "consolidation_group": consolidation_map.get(task["task_id"]),
        })
        scored.append(task_entry)

    scored.sort(key=lambda x: x["weighted_priority"], reverse=True)
    unique_groups = len(set(v for v in consolidation_map.values()))

    log.info(
        "Negotiation complete run_id=%s inflated=%d groups=%d",
        run_id,
        sum(1 for s in scored if s["inflated_claim"]),
        unique_groups,
    )

    return {
        "negotiation_run_id": run_id,
        "scored_tasks": scored,
        "total_tasks": len(scored),
        "inflated_count": sum(1 for s in scored if s["inflated_claim"]),
        "consolidation_groups": unique_groups,
        "conflicts": conflicts,
    }


def is_available() -> bool:
    return True
