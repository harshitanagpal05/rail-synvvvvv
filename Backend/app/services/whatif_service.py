"""RailSync 2.0 — What-if disruption service.

NEVER modifies the current plan. Clones planning state, injects disruption,
re-optimizes using Layer 3 reoptimize_fast, and diffs against the baseline plan.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from Optimization import DisruptionScenario, MaintenanceTask, TaskChangeDiff, WhatIfResult
from app.core.logging import get_logger
from app.db import repositories as repo
from app.integrations import layer3
from app.schemas.optimization import (
    AssignmentOut,
    PlanDiff,
    WhatIfRequest,
    WhatIfResponse,
)
from app.services import risk_service, task_service
from railsync.layer0.generator import generate_timetable

log = get_logger("service.whatif")


def run_whatif(db: Session, request: WhatIfRequest) -> WhatIfResponse:
    """Run a what-if disruption simulation using Layer 3 reoptimize_fast."""
    try:
        whatif_start = time.perf_counter()
        run_id = f"WIF-{uuid.uuid4().hex[:8].upper()}"
        log.info(
            "What-if started run_id=%s scenario_id=%s type=%s segment=%s severity=%s",
            run_id, request.scenario_id, request.type, request.segment_id, request.severity,
        )

        # 1. Load baseline tasks & risk data
        tasks = task_service.get_pending_tasks(db)
        risk_data = risk_service.get_risk_data_map(db)

        event_type = request.type or request.event_type
        event_time_str = request.time or request.event_time
        scenario_id = request.scenario_id or f"SCN-{uuid.uuid4().hex[:6].upper()}"
        description = request.description or f"Disruption simulation for {event_type or 'unplanned event'}"

        emergency_tasks: list[MaintenanceTask] = []
        if request.emergency_tasks:
            for et in request.emergency_tasks:
                emergency_tasks.append(layer3.transform_task(et, risk_data))

        # Support synthetic emergency task from event parameters
        if event_type and request.segment_id:
            synth_task = _create_disruption_task(request)
            emergency_tasks.append(layer3.transform_task(synth_task, risk_data))

        timetable = generate_timetable(seed=42)
        base_date = datetime(2026, 9, 15, 0, 0, 0)
        all_blocks = layer3.build_block_windows(timetable=timetable, horizon_days=7, base_date=base_date)

        # Enforce chronological consistency: elapsed blocks cannot receive newly injected emergencies
        cancelled_blocks_set = set(request.cancelled_blocks or [])
        if event_time_str:
            parse_hr = 0
            parse_mn = 0
            try:
                parts = event_time_str.split(" ")[-1].split(":")
                parse_hr = int(parts[0])
                parse_mn = int(parts[1]) if len(parts) > 1 else 0
            except (ValueError, IndexError):
                pass

            event_dt = base_date.replace(hour=parse_hr, minute=parse_mn)
            for b in all_blocks:
                try:
                    b_end = datetime.strptime(b.end_time, "%Y-%m-%d %H:%M")
                    if b_end <= event_dt:
                        cancelled_blocks_set.add(b.block_id)
                except Exception:
                    pass

        disruption = DisruptionScenario(
            scenario_id=scenario_id,
            description=description,
            emergency_tasks=emergency_tasks,
            cancelled_blocks=list(cancelled_blocks_set),
            modified_passenger_conflicts=request.modified_passenger_conflicts or {},
            modified_block_durations=request.modified_block_durations or {},
            locked_assignments=request.locked_assignments or {},
        )

        # 3. Invoke Layer 3 Fast Re-optimization
        whatif_res: WhatIfResult = layer3.run_fast_reoptimization(
            baseline_tasks=tasks,
            risk_data=risk_data,
            timetable=timetable,
            disruption=disruption,
            base_date=base_date,
        )

        elapsed_ms = int((time.perf_counter() - whatif_start) * 1000)
        is_feasible = whatif_res.solver_status in ("OPTIMAL", "FEASIBLE")

        if not is_feasible:
            log.warning("What-if infeasible run_id=%s solver_status=%s", run_id, whatif_res.solver_status)
            return WhatIfResponse(
                feasible=False,
                run_id=run_id,
                scenario_id=scenario_id,
                reason=[f"Re-optimization returned {whatif_res.solver_status}: {whatif_res.summary}"],
                execution_time_ms=elapsed_ms,
                solver_status=whatif_res.solver_status,
                summary=whatif_res.summary,
            )

        # 4. Map schedules and build block lookup
        all_blocks = layer3.build_block_windows(timetable=timetable, horizon_days=7, base_date=base_date)
        block_lookup = {b.block_id: b for b in all_blocks}
        task_meta = {str(t["task_id"]): t for t in tasks}

        current_plan = repo.get_current_plan(db)
        policy = current_plan.policy if current_plan else "balanced"
        plan_id = f"PLAN-WIF-{uuid.uuid4().hex[:8].upper()}"

        # 5. Persist what-if run & plan (NOT current)
        repo.save_optimization_run(db, **{
            "run_id": f"OPT-{run_id}",
            "policy": policy,
            "horizon": "weekly",
            "status": whatif_res.solver_status.lower(),
            "execution_time_ms": elapsed_ms,
            "objective_values": {
                "solver_objective": whatif_res.revised_schedule.objective_value,
                "scheduled_tasks_count": whatif_res.revised_schedule.scheduled_tasks_count,
                "unassigned_tasks_count": whatif_res.revised_schedule.unassigned_tasks_count,
                "total_freight_delays": whatif_res.revised_schedule.total_freight_trains_delayed,
            },
            "robustness_score": 1.0,
            "input_summary": {"what_if": True, "disruption": request.model_dump()},
            "output_summary": {"assignments": whatif_res.revised_schedule.scheduled_tasks_count},
        })

        repo.save_block_plan(db, **{
            "plan_id": plan_id,
            "optimization_run_id": f"OPT-{run_id}",
            "plan_type": "what_if",
            "policy": policy,
            "status": "simulated",
            "is_current": False,
        })

        # Upsert emergency tasks into database so foreign key constraints are satisfied
        for em in disruption.emergency_tasks:
            crit_int = 5 if em.claimed_criticality == "CRITICAL" else (4 if em.claimed_criticality == "HIGH" else (3 if em.claimed_criticality == "MEDIUM" else 2))
            repo.upsert_task(db, **{
                "task_id": em.task_id,
                "segment_id": em.segment,
                "department": "TRACK",
                "task_type": em.description or "Emergency Defect",
                "claimed_criticality": crit_int,
                "min_duration_hrs": em.min_duration_hrs,
                "preferred_window_start": base_date,
                "preferred_window_end": base_date + timedelta(hours=6),
                "overdue": True,
                "status": "disruption",
            })


        # 6. Format Plan B assignments and diffs
        plan_b_assignments: list[AssignmentOut] = []
        for st in whatif_res.revised_schedule.scheduled_tasks:
            if st.status == "SCHEDULED" and st.assigned_block:
                blk = block_lookup.get(st.assigned_block)
                b_start = None
                b_end = None
                if blk:
                    try:
                        b_start = datetime.strptime(blk.start_time, "%Y-%m-%d %H:%M")
                        b_end = datetime.strptime(blk.end_time, "%Y-%m-%d %H:%M")
                    except Exception:
                        b_start = base_date + timedelta(days=blk.day_index, hours=1)
                        b_end = b_start + timedelta(hours=st.duration_hrs)
                else:
                    b_start = base_date + timedelta(days=st.window_index or 0, hours=1)
                    b_end = b_start + timedelta(hours=st.duration_hrs)

                meta = task_meta.get(st.task_id, {})
                seg_risk = risk_data.get(st.segment, {}) if risk_data else {}
                exp_downtime = meta.get("expected_downtime_days")
                if exp_downtime is None:
                    exp_downtime = seg_risk.get("expected_downtime_days")

                a_out = AssignmentOut(
                    task_id=st.task_id,
                    segment_id=st.segment,
                    department=meta.get("department", "TRACK"),
                    block_start=b_start,
                    block_end=b_end,
                    duration_hrs=st.duration_hrs,
                    priority=meta.get("weighted_priority", 3.0),
                    risk_30d=st.risk_30d,
                    reason=st.remarks,
                    explanation={
                        "primary_reason": st.remarks or "Scheduled into optimal conflict-free possession window.",
                        "claimed_criticality": st.claimed_criticality,
                        "risk_30d": st.risk_30d,
                        "expected_downtime_days": exp_downtime,
                        "duration_hrs": st.duration_hrs,
                        "assigned_block": st.assigned_block,
                        "passenger_conflict": "avoided",
                        "freight_delays": st.freight_conflict_count,
                        "is_high_risk": st.is_high_risk_critical,
                        "window_index": st.window_index,
                        "confidence": meta.get("confidence") or seg_risk.get("confidence"),
                    },
                    constraint_summary={
                        "assigned_block": st.assigned_block,
                        "freight_delay_penalty": st.freight_penalty_score,
                        "is_high_risk": st.is_high_risk_critical,
                    },
                    consolidation_group=meta.get("consolidation_group"),
                    status=st.status,
                    assigned_block=st.assigned_block,
                    why=st.remarks or "Assigned after emergency re-optimization",
                )
                plan_b_assignments.append(a_out)

                repo.save_assignment(db, **{
                    "plan_id": plan_id,
                    "task_id": a_out.task_id,
                    "segment_id": a_out.segment_id,
                    "department": a_out.department,
                    "block_start": a_out.block_start,
                    "block_end": a_out.block_end,
                    "duration_hrs": a_out.duration_hrs,
                    "priority": a_out.priority,
                    "risk_30d": a_out.risk_30d,
                    "reason": a_out.reason,
                    "explanation": a_out.explanation,
                    "consolidation_group": a_out.consolidation_group,
                })

        db.commit()

        # 7. Convert Layer 3 affected tasks to PlanDiff
        plan_diffs: list[PlanDiff] = []
        reasons: list[str] = []
        for diff in whatif_res.affected_tasks:
            plan_diffs.append(
                PlanDiff(
                    task_id=diff.task_id,
                    change_type=diff.change_type.lower(),
                    original_block=diff.original_block,
                    new_block=diff.new_block,
                    reason=diff.reason,
                )
            )
            reasons.append(diff.reason)

        if not reasons and whatif_res.summary:
            reasons.append(whatif_res.summary)

        # Added / removed task assignments
        base_scheduled = {t.task_id: t for t in whatif_res.baseline_schedule.scheduled_tasks if t.status == "SCHEDULED"}
        rev_scheduled = {t.task_id: t for t in whatif_res.revised_schedule.scheduled_tasks if t.status == "SCHEDULED"}

        added_outs = [a for a in plan_b_assignments if a.task_id not in base_scheduled]
        removed_outs = []
        for tid, st in base_scheduled.items():
            if tid not in rev_scheduled:
                meta = task_meta.get(tid, {})
                removed_outs.append(
                    AssignmentOut(
                        task_id=st.task_id,
                        segment_id=st.segment,
                        department=meta.get("department", "TRACK"),
                        block_start=base_date,
                        block_end=base_date + timedelta(hours=st.duration_hrs),
                        duration_hrs=st.duration_hrs,
                        priority=meta.get("weighted_priority", 3.0),
                        risk_30d=st.risk_30d,
                        reason=f"Deferred due to disruption: {st.remarks}",
                    )
                )

        log.info(
            "What-if complete run_id=%s plan_b=%s diffs=%d elapsed=%dms",
            run_id, plan_id, len(plan_diffs), elapsed_ms,
        )

        return WhatIfResponse(
            feasible=True,
            run_id=run_id,
            scenario_id=scenario_id,
            plan_b={
                "plan_id": plan_id,
                "policy": policy,
                "assignments": len(plan_b_assignments),
                "status": "simulated",
            },
            changed_assignments=plan_diffs,
            added_assignments=added_outs,
            removed_assignments=removed_outs,
            reason=reasons,
            execution_time_ms=elapsed_ms,
            objective_values={
                "solver_objective": whatif_res.revised_schedule.objective_value,
                "scheduled_tasks_count": whatif_res.revised_schedule.scheduled_tasks_count,
                "unassigned_tasks_count": whatif_res.revised_schedule.unassigned_tasks_count,
                "total_freight_delays": whatif_res.revised_schedule.total_freight_trains_delayed,
            },
            solver_status=whatif_res.solver_status,
            summary=whatif_res.summary,
        )
    except Exception as e:
        log.exception("Error in run_whatif: %s", e)
        raise




def _create_disruption_task(request: WhatIfRequest) -> dict[str, Any]:
    """Create a synthetic high-priority task from a disruption event."""
    parse_hour = 8
    if request.time:
        try:
            parts = request.time.split(":")
            parse_hour = int(parts[0])
        except (ValueError, IndexError):
            pass

    severity_to_crit = {"low": 3, "moderate": 4, "critical": 5, "emergency": 5, "high": 4}
    crit = severity_to_crit.get(str(request.severity).lower(), 4)

    base = datetime(2026, 9, 15, parse_hour, 0, 0)
    return {
        "task_id": f"DISRUPTION-{uuid.uuid4().hex[:6].upper()}",
        "segment_id": request.segment_id or "SEG-DISRUPTION",
        "department": "TRACK",
        "task_type": request.type or "Emergency Defect",
        "claimed_criticality": crit,
        "min_duration_hrs": 2.0 if request.severity not in ("critical", "emergency") else 3.0,
        "overdue": True,
        "preferred_window_start": base,
        "preferred_window_end": base + timedelta(hours=6),
        "weighted_priority": float(crit) + 1.0,
        "risk_30d": 0.95 if crit == 5 else 0.80,
    }

