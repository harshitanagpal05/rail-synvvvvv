"""RailSync 2.0 — Comprehensive Layer 1 ML to Layer 3 Optimization Integration Tests.

Validates that Layer 1 ML outputs (risk_30d, expected_downtime_days, preventive_block_duration_hrs,
confidence, overrun_probability, cold_start_fallback, survival_curve) flow into Layer 3
MaintenanceTask correctly, duration fallbacks respect operational requirements, and existing
CP-SAT constraints and planning algorithms function without regression.
"""

from __future__ import annotations

import pytest
from app.integrations import layer3
from Optimization import (
    MaintenanceTask,
    BlockWindow,
    OptimizerConfig,
    optimize_schedule,
    reoptimize_fast,
    generate_weekly_plan,
    generate_monthly_plan,
    evaluate_scenario_robustness,
    DisruptionScenario,
)


def test_1_ml_risk_30d_reaches_maintenance_task():
    """Verify that Layer 1 risk_30d is correctly transferred to MaintenanceTask."""
    task_dict = {"task_id": "T-RISK-01", "segment_id": "SEG-TEST-001", "claimed_criticality": 4}
    risk_dict = {"SEG-TEST-001": {"risk_30d": 0.88}}
    task = layer3.transform_task(task_dict, risk_dict)
    assert task.risk_30d == 0.88


def test_2_expected_downtime_days_reaches_maintenance_task():
    """Verify that Layer 1 expected_downtime_days is transferred to MaintenanceTask."""
    task_dict = {"task_id": "T-DOWN-01", "segment_id": "SEG-TEST-001", "claimed_criticality": 3}
    risk_dict = {"SEG-TEST-001": {"risk_30d": 0.5, "expected_downtime_days": 3.75}}
    task = layer3.transform_task(task_dict, risk_dict)
    assert task.expected_downtime_days == 3.75


def test_3_preventive_block_duration_hrs_fallback_when_missing():
    """Verify that ML preventive_block_duration_hrs is used when task has no explicit duration."""
    task_dict = {"task_id": "T-DUR-01", "segment_id": "SEG-TEST-001", "claimed_criticality": 3}
    risk_dict = {"SEG-TEST-001": {"risk_30d": 0.4, "preventive_block_duration_hrs": 3.5}}
    task = layer3.transform_task(task_dict, risk_dict)
    assert task.min_duration_hrs == 3.5


def test_4_explicit_task_duration_not_overwritten():
    """Verify that a valid explicit task duration is NOT overwritten by ML duration."""
    task_dict = {
        "task_id": "T-DUR-02",
        "segment_id": "SEG-TEST-001",
        "claimed_criticality": 3,
        "min_duration_hrs": 4.5,
    }
    risk_dict = {"SEG-TEST-001": {"risk_30d": 0.4, "preventive_block_duration_hrs": 2.0}}
    task = layer3.transform_task(task_dict, risk_dict)
    assert task.min_duration_hrs == 4.5  # Explicit 4.5 is preserved, NOT 2.0


def test_5_overrun_probability_reaches_maintenance_task():
    """Verify that Layer 1 overrun_probability is transferred to MaintenanceTask."""
    task_dict = {"task_id": "T-OVR-01", "segment_id": "SEG-TEST-001"}
    risk_dict = {"SEG-TEST-001": {"overrun_probability": 0.28}}
    task = layer3.transform_task(task_dict, risk_dict)
    assert task.overrun_probability == 0.28


def test_6_confidence_reaches_maintenance_task():
    """Verify that Layer 1 confidence is transferred to MaintenanceTask."""
    task_dict = {"task_id": "T-CONF-01", "segment_id": "SEG-TEST-001"}
    risk_dict = {"SEG-TEST-001": {"confidence": "high"}}
    task = layer3.transform_task(task_dict, risk_dict)
    assert task.confidence == "high"


def test_7_cold_start_fallback_reaches_maintenance_task():
    """Verify that Layer 1 cold_start_fallback is transferred to MaintenanceTask."""
    task_dict = {"task_id": "T-COLD-01", "segment_id": "SEG-TEST-001"}
    risk_dict = {"SEG-TEST-001": {"cold_start_fallback": True}}
    task = layer3.transform_task(task_dict, risk_dict)
    assert task.cold_start_fallback is True


def test_8_high_risk_critical_hard_scheduling_rule():
    """Verify high-risk + critical hard scheduling rule: must be assigned to earliest feasible window."""
    high_risk_task = MaintenanceTask(
        task_id="T-HIGH-CRIT",
        segment="SEG-01",
        claimed_criticality="CRITICAL",
        min_duration_hrs=2.0,
        risk_30d=0.85,  # > 0.70 threshold
    )
    blocks = [
        BlockWindow(block_id="BLK-EARLY", start_time="01:00", end_time="04:00", duration_hrs=3.0, window_index=0),
        BlockWindow(block_id="BLK-LATE", start_time="01:00", end_time="04:00", duration_hrs=3.0, window_index=1),
    ]
    cfg = OptimizerConfig.safety_first()
    result = optimize_schedule(tasks=[high_risk_task], blocks=blocks, config=cfg)
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert result.scheduled_tasks[0].assigned_block == "BLK-EARLY"


def test_9_locked_assignments_still_enforced():
    """Verify that locked assignments are strictly enforced as hard constraints."""
    from Optimization import RailSyncOptimizer
    task1 = MaintenanceTask(task_id="T-LOCK", segment="SEG-01", claimed_criticality="MEDIUM", min_duration_hrs=2.0, risk_30d=0.3)
    task2 = MaintenanceTask(task_id="T-OTHER", segment="SEG-02", claimed_criticality="HIGH", min_duration_hrs=2.0, risk_30d=0.7)
    blocks = [
        BlockWindow(block_id="BLK-01", start_time="01:00", end_time="04:00", duration_hrs=3.0, window_index=0),
        BlockWindow(block_id="BLK-02", start_time="01:00", end_time="04:00", duration_hrs=3.0, window_index=1),
    ]
    optimizer = RailSyncOptimizer()
    result = optimizer.optimize(
        tasks=[task1, task2],
        blocks=blocks,
        locked_assignments={"T-LOCK": "BLK-02"},
    )
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    sched_map = {t.task_id: t for t in result.scheduled_tasks}
    assert sched_map["T-LOCK"].assigned_block == "BLK-02"


def test_10_passenger_conflict_remains_hard():
    """Verify that passenger train conflict is a hard constraint (task rejected from conflicted block)."""
    task = MaintenanceTask(task_id="T-PASS", segment="SEG-01", claimed_criticality="MEDIUM", min_duration_hrs=2.0, risk_30d=0.3)
    blocks = [
        BlockWindow(
            block_id="BLK-PASS-CONFLICT",
            start_time="01:00",
            end_time="04:00",
            duration_hrs=3.0,
            window_index=0,
            passenger_conflicts={"SEG-01": 2},  # 2 passenger trains on SEG-01
        )
    ]
    result = optimize_schedule(tasks=[task], blocks=blocks)
    # Task must NOT be scheduled in BLK-PASS-CONFLICT
    assert result.scheduled_tasks[0].status == "UNASSIGNED"
    assert result.unassigned_tasks_count == 1


def test_11_freight_conflict_remains_soft():
    """Verify that freight train conflict is permitted with a soft penalty."""
    task = MaintenanceTask(task_id="T-FRT", segment="SEG-01", claimed_criticality="MEDIUM", min_duration_hrs=2.0, risk_30d=0.3)
    blocks = [
        BlockWindow(
            block_id="BLK-FREIGHT",
            start_time="01:00",
            end_time="04:00",
            duration_hrs=3.0,
            window_index=0,
            freight_conflicts={"SEG-01": 1},  # 1 freight train on SEG-01
        )
    ]
    result = optimize_schedule(tasks=[task], blocks=blocks)
    assert result.solver_status in ("OPTIMAL", "FEASIBLE")
    assert result.scheduled_tasks[0].status == "SCHEDULED"
    assert result.scheduled_tasks[0].assigned_block == "BLK-FREIGHT"
    assert result.total_freight_trains_delayed == 1


def test_12_monthly_and_weekly_planning_with_ml_metadata():
    """Verify weekly and monthly planning operate smoothly and produce downtime metrics."""
    task = MaintenanceTask(
        task_id="T-PLAN-01",
        segment="SEG-01",
        claimed_criticality="HIGH",
        min_duration_hrs=2.5,
        risk_30d=0.75,
        expected_downtime_days=2.5,
        overrun_probability=0.12,
    )
    blocks = [
        BlockWindow(block_id=f"BLK-D{d}", start_time="01:00", end_time="05:00", duration_hrs=4.0, day_index=d, window_index=d)
        for d in range(7)
    ]
    weekly = generate_weekly_plan(tasks=[task], blocks=blocks)
    assert weekly.schedule.scheduled_tasks_count == 1

    monthly = generate_monthly_plan(tasks=[task], blocks=blocks)
    assert monthly.schedule.scheduled_tasks_count == 1
    assert "total_expected_downtime_days" in monthly.horizon_summary
    assert monthly.horizon_summary["total_expected_downtime_days"] == 2.5


def test_13_whatif_reoptimization_with_ml_metadata():
    """Verify what-if fast re-optimization with ML metadata."""
    baseline_task = MaintenanceTask(
        task_id="T-BASE-01", segment="SEG-01", claimed_criticality="MEDIUM", min_duration_hrs=2.0, risk_30d=0.4,
        expected_downtime_days=1.2, overrun_probability=0.08
    )
    emergency_task = MaintenanceTask(
        task_id="T-EMERG-01", segment="SEG-01", claimed_criticality="CRITICAL", min_duration_hrs=2.0, risk_30d=0.95,
        expected_downtime_days=5.0, overrun_probability=0.40
    )
    blocks = [
        BlockWindow(block_id="BLK-01", start_time="01:00", end_time="04:00", duration_hrs=3.0, window_index=0),
        BlockWindow(block_id="BLK-02", start_time="01:00", end_time="04:00", duration_hrs=3.0, window_index=1),
    ]
    disruption = DisruptionScenario(
        scenario_id="SCN-TEST-ML",
        description="Emergency fracture on SEG-01",
        emergency_tasks=[emergency_task],
    )
    whatif_res = reoptimize_fast(tasks=[baseline_task], blocks=blocks, disruption=disruption)
    assert whatif_res.solver_status in ("OPTIMAL", "FEASIBLE")
    assert whatif_res.revised_schedule.solver_run_time_seconds < 5.0
    assert len(whatif_res.affected_tasks) > 0


def test_14_robustness_evaluation_with_ml_survival_curve():
    """Verify that Monte Carlo robustness evaluation runs with ML empirical survival curves."""
    empirical_curve = [{"day": d, "survival_probability": 1.0 - (d * 0.02)} for d in range(1, 31)]
    task = MaintenanceTask(
        task_id="T-ROB-01", segment="SEG-01", claimed_criticality="HIGH", min_duration_hrs=2.0, risk_30d=0.6,
        survival_curve=empirical_curve
    )
    blocks = [BlockWindow(block_id="BLK-01", start_time="01:00", end_time="04:00", duration_hrs=3.0, window_index=0)]
    rob = evaluate_scenario_robustness(tasks=[task], blocks=blocks, num_scenarios=25)
    assert rob.total_scenarios == 25
    assert rob.robustness_percentage >= 0.0
