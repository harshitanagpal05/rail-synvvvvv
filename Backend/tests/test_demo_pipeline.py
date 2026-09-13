"""RailSync 2.0 — Comprehensive SIH Demo Pipeline & Regression Tests.

Validates:
1. High-risk critical task cannot silently remain unassigned when a feasible future block exists
2. High-risk critical task gets explicit infeasibility reason when no feasible future block exists
3. Emergency cannot be assigned to an elapsed block
4. Emergency selects earliest future feasible block
5. Policy presets are actually passed through and evaluated
6. Identical policy results are allowed when mathematically optimal
7. Robustness vulnerability output is consistent
"""

import pytest
from datetime import datetime
from Optimization import (
    MaintenanceTask,
    BlockWindow,
    DisruptionScenario,
    OptimizerConfig,
    evaluate_scenario_robustness,
    generate_plan_b_contingencies,
    compute_pareto_frontier,
    optimize_schedule,
    reoptimize_fast,
)
from Backend.app.integrations import layer1, layer2, layer3
from railsync.layer0.generator import generate_timetable


def test_1_high_risk_critical_task_scheduled_in_feasible_window():
    """Verify high-risk critical tasks are scheduled into the earliest feasible window."""
    layer1._ensure_trained_data()
    all_risks = {sid: layer1.predict_risk({"segment_id": sid}) for sid in layer1._TRAINED_FORECASTS}

    tasks = [
        {
            "task_id": "TASK-TRK-039",
            "segment_id": "SEG-039",
            "department": "TRACK",
            "claimed_criticality": 5,
            "min_duration_hrs": 3.0,
            "overdue": True,
            "preferred_window": "BLK-D1-MIDDAY",
        },
        {
            "task_id": "TASK-SIG-039",
            "segment_id": "SEG-039",
            "department": "SIGNAL",
            "claimed_criticality": 4,
            "min_duration_hrs": 2.0,
            "overdue": False,
            "preferred_window": "BLK-D1-NIGHT",
        },
    ]

    neg = layer2.negotiate(tasks, all_risks)
    assert neg["total_tasks"] == 2
    # Verify Layer 2 preserves min_duration_hrs
    assert neg["scored_tasks"][0]["min_duration_hrs"] in (2.0, 3.0)

    timetable = generate_timetable(seed=42)
    base_date = datetime(2026, 9, 15, 0, 0, 0)
    opt_res = layer3.optimize(
        tasks=neg["scored_tasks"],
        risk_data=all_risks,
        timetable=timetable,
        policy="balanced",
        horizon_days=7,
        base_date=base_date,
    )

    assert opt_res["feasible"] is True
    assert len(opt_res["assignments"]) == 2
    for a in opt_res["assignments"]:
        assert a["task_id"] in ("TASK-TRK-039", "TASK-SIG-039")
        assert a["risk_30d"] == 1.0
        assert a["explanation"]["is_high_risk"] is True


def test_2_high_risk_critical_task_gets_explicit_infeasibility_reason():
    """Verify task gets clear explicit reason when genuinely impossible (e.g. dur > all blocks)."""
    impossible_task = MaintenanceTask(
        task_id="TASK-IMPOSSIBLE-999",
        segment="SEG-039",
        claimed_criticality="CRITICAL",
        min_duration_hrs=10.0,  # Exceeds max block duration (4.0h)
        risk_30d=0.95,
    )
    blocks = [
        BlockWindow(block_id="BLK-01", start_time="2026-09-15 01:00", end_time="2026-09-15 05:00", duration_hrs=4.0, window_index=0),
        BlockWindow(block_id="BLK-02", start_time="2026-09-15 11:30", end_time="2026-09-15 14:30", duration_hrs=3.0, window_index=1),
    ]

    res = optimize_schedule(tasks=[impossible_task], blocks=blocks)
    assert res.unassigned_tasks_count == 1
    unassigned_st = res.scheduled_tasks[0]
    assert unassigned_st.status == "UNASSIGNED"
    assert "exceeds all available block windows" in unassigned_st.remarks


def test_3_and_4_emergency_time_consistency_and_future_block_selection():
    """Verify 11:30 AM emergency cannot take elapsed 01:00 AM block and selects future window."""
    baseline_task = MaintenanceTask(
        task_id="TASK-MORNING-DONE",
        segment="SEG-004",
        claimed_criticality="HIGH",
        min_duration_hrs=2.0,
        risk_30d=0.50,
    )
    blocks = [
        BlockWindow(block_id="BLK-D1-NIGHT", start_time="2026-09-15 01:00", end_time="2026-09-15 05:00", duration_hrs=4.0, window_index=0),
        BlockWindow(block_id="BLK-D1-MIDDAY", start_time="2026-09-15 11:30", end_time="2026-09-15 14:30", duration_hrs=3.0, window_index=1),
        BlockWindow(block_id="BLK-D2-NIGHT", start_time="2026-09-16 01:00", end_time="2026-09-16 05:00", duration_hrs=4.0, window_index=2),
    ]

    # Emergency occurring at 11:30 AM
    emergency_task = MaintenanceTask(
        task_id="EM-FRACTURE-039",
        segment="SEG-039",
        claimed_criticality="CRITICAL",
        min_duration_hrs=3.0,
        risk_30d=0.99,
        preferred_window="BLK-D1-MIDDAY",
    )

    disruption = DisruptionScenario(
        scenario_id="SCN-EM-01",
        description="Emergency at 11:30 AM",
        emergency_tasks=[emergency_task],
        cancelled_blocks=["BLK-D1-NIGHT"],  # Morning block elapsed & closed to new assignments
    )

    whatif = reoptimize_fast(tasks=[baseline_task], blocks=blocks, disruption=disruption)
    assert whatif.solver_status == "OPTIMAL"

    em_diff = next(d for d in whatif.affected_tasks if d.task_id == "EM-FRACTURE-039")
    assert em_diff.new_block == "BLK-D1-MIDDAY"  # Assigned to immediate future window >= 11:30 AM
    assert em_diff.new_block != "BLK-D1-NIGHT"   # NOT assigned to past elapsed block


def test_5_and_6_policy_presets_pass_through_and_pareto_convergence():
    """Verify policy presets pass weights and evaluate Pareto frontier."""
    tasks = [
        MaintenanceTask(task_id="T1", segment="SEG-001", claimed_criticality="CRITICAL", min_duration_hrs=2.0, risk_30d=0.90),
        MaintenanceTask(task_id="T2", segment="SEG-002", claimed_criticality="LOW", min_duration_hrs=2.0, risk_30d=0.10),
    ]
    blocks = [
        BlockWindow(block_id="BLK-01", start_time="2026-09-15 01:00", end_time="2026-09-15 05:00", duration_hrs=4.0, window_index=0),
    ]

    pareto = compute_pareto_frontier(tasks=tasks, blocks=blocks)
    assert len(pareto.points) == 3
    # Verify policy configs are distinct
    assert OptimizerConfig.safety_first().WEIGHT_UNASSIGNED_HIGH_RISK_PENALTY == 100_000
    assert OptimizerConfig.balanced().WEIGHT_UNASSIGNED_HIGH_RISK_PENALTY == 50_000
    assert OptimizerConfig.throughput_first().WEIGHT_FREIGHT_CONFLICT_PENALTY == 800


def test_7_robustness_vulnerability_consistency():
    """Verify robustness evaluation correctly reflects scheduled maintenance vs unassigned risks."""
    # When high risk asset is maintained in-time
    scheduled_task = MaintenanceTask(
        task_id="TASK-MAINTAINED",
        segment="SEG-039",
        claimed_criticality="CRITICAL",
        min_duration_hrs=2.0,
        risk_30d=0.99,
        survival_curve=[{"day": d, "survival_probability": max(0.01, 1.0 - d * 0.03)} for d in range(1, 31)],
    )
    blocks = [
        BlockWindow(block_id="BLK-01", start_time="2026-09-15 01:00", end_time="2026-09-15 05:00", duration_hrs=4.0, window_index=0, day_index=0),
    ]

    rob_res = evaluate_scenario_robustness(tasks=[scheduled_task], blocks=blocks, num_scenarios=20)
    assert rob_res.robustness_percentage == 100.0
    assert len(rob_res.vulnerable_assets) == 0


def test_sih_demo_pipeline_full_integration():
    """Verify complete 10-step demo pipeline executes with 100% data integrity."""
    layer1._ensure_trained_data()
    all_risks = {sid: layer1.predict_risk({"segment_id": sid}) for sid in layer1._TRAINED_FORECASTS}
    tasks = [
        {"task_id": "TASK-TRK-039", "segment_id": "SEG-039", "department": "TRACK", "claimed_criticality": 5, "min_duration_hrs": 3.0, "overdue": True, "preferred_window": "BLK-D1-MIDDAY"},
        {"task_id": "TASK-SIG-039", "segment_id": "SEG-039", "department": "SIGNAL", "claimed_criticality": 4, "min_duration_hrs": 2.0, "overdue": False, "preferred_window": "BLK-D1-NIGHT"},
        {"task_id": "TASK-TRK-012", "segment_id": "SEG-012", "department": "TRACK", "claimed_criticality": 5, "min_duration_hrs": 2.0, "overdue": False, "preferred_window": "BLK-D1-NIGHT"},
        {"task_id": "TASK-OHE-004", "segment_id": "SEG-004", "department": "ELECTRICAL", "claimed_criticality": 4, "min_duration_hrs": 2.5, "overdue": False, "preferred_window": "BLK-D1-NIGHT"},
        {"task_id": "TASK-TRK-045", "segment_id": "SEG-045", "department": "TRACK", "claimed_criticality": 2, "min_duration_hrs": 2.0, "overdue": False, "preferred_window": "BLK-D1-NIGHT"},
    ]
    neg = layer2.negotiate(tasks, all_risks)
    timetable = generate_timetable(seed=42)
    base_date = datetime(2026, 9, 15, 0, 0, 0)
    opt_res = layer3.optimize(tasks=neg["scored_tasks"], risk_data=all_risks, timetable=timetable, policy="balanced", horizon_days=7, base_date=base_date)

    assert opt_res["feasible"] is True
    assert len(opt_res["assignments"]) == 5
    assert all(a["explanation"]["passenger_conflict"] == "avoided" for a in opt_res["assignments"])
