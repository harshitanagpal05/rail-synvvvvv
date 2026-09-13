"""
test_optimizer.py - Comprehensive Unit & Scenario Tests for RailSync Optimizer
=============================================================================
Tests all 9 required operational scenarios for Layer 3 CP-SAT Optimization:
1. Normal task scheduling
2. Passenger train conflict rejection (HARD constraint)
3. Freight train conflict allowance with soft penalty
4. High-risk critical task forced into next feasible window (HARD constraint)
5. Multiple tasks on DIFFERENT segments sharing the same block
6. Two tasks on the SAME segment NOT sharing the same block (HARD exclusivity)
7. Task duration exceeding block length rejection (HARD constraint)
8. Unassignable task handling and clear reporting
9. What-If dynamic disruption and re-optimization
"""

import unittest
import sys
import os

# Support running tests directly or via unittest runner
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from Optimization import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ScheduledTaskResult,
        DisruptionScenario,
        WhatIfResult,
        MultiHorizonScheduleResult,
        ParetoPoint,
        ParetoFrontierResult,
        ScenarioRobustnessResult,
        PlanBContingency,
        PlanBRepository,
        PolicyPreset,
        HorizonType,
        OptimizerConfig,
        DEFAULT_CONFIG,
        RailSyncOptimizer,
        WhatIfEngine,
        SurvivalCurveModel,
        ScenarioRobustnessEngine,
        MultiHorizonPlanner,
        ParetoFrontierAnalyzer,
        ContingencyEngine,
        optimize_schedule,
        what_if_reoptimize,
        generate_weekly_plan,
        generate_monthly_plan,
        compute_pareto_frontier,
        evaluate_scenario_robustness,
        generate_plan_b_contingencies,
        reoptimize_fast,
    )
except ImportError:
    from models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ScheduledTaskResult,
        DisruptionScenario,
        WhatIfResult,
        MultiHorizonScheduleResult,
        ParetoPoint,
        ParetoFrontierResult,
        ScenarioRobustnessResult,
        PlanBContingency,
        PlanBRepository,
        PolicyPreset,
        HorizonType,
    )
    from config import OptimizerConfig, DEFAULT_CONFIG
    from optimizer import (
        RailSyncOptimizer,
        optimize_schedule,
        what_if_reoptimize,
        generate_weekly_plan,
        generate_monthly_plan,
        compute_pareto_frontier,
        evaluate_scenario_robustness,
        generate_plan_b_contingencies,
        reoptimize_fast,
    )
    from what_if import WhatIfEngine
    from robustness import SurvivalCurveModel, ScenarioRobustnessEngine
    from multi_horizon import MultiHorizonPlanner
    from pareto import ParetoFrontierAnalyzer
    from contingency import ContingencyEngine




class TestRailSyncOptimizer(unittest.TestCase):

    def setUp(self):
        """Set up standard test optimizer instance."""
        self.config = OptimizerConfig()
        self.optimizer = RailSyncOptimizer(config=self.config)

    # --------------------------------------------------------------------------
    # Test 1: Normal Task Scheduling
    # --------------------------------------------------------------------------
    def test_1_normal_task_scheduling(self):
        """Verify normal feasible maintenance tasks are scheduled properly."""
        tasks = [
            MaintenanceTask(
                task_id="T1",
                segment="SEC-1",
                claimed_criticality="MEDIUM",
                min_duration_hrs=2.0,
                risk_30d=0.40,
            )
        ]
        blocks = [
            BlockWindow(
                block_id="B1",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,
                window_index=0,
            )
        ]

        result = self.optimizer.optimize(tasks, blocks)

        self.assertIn(result.solver_status, ("OPTIMAL", "FEASIBLE"))
        self.assertEqual(result.scheduled_tasks_count, 1)
        self.assertEqual(result.unassigned_tasks_count, 0)
        self.assertEqual(result.scheduled_tasks[0].assigned_block, "B1")
        self.assertEqual(result.scheduled_tasks[0].status, "SCHEDULED")

    # --------------------------------------------------------------------------
    # Test 2: Passenger Conflict Being Rejected (HARD constraint)
    # --------------------------------------------------------------------------
    def test_2_passenger_conflict_rejection(self):
        """Verify a task is NEVER scheduled in a block that has passenger conflicts on that segment."""
        tasks = [
            MaintenanceTask(
                task_id="T_PASS_TEST",
                segment="SEC-NDLS-GZB",
                claimed_criticality="HIGH",
                min_duration_hrs=2.0,
                risk_30d=0.60,
            )
        ]
        # B1 has passenger conflict (HARD violation), B2 does not
        blocks = [
            BlockWindow(
                block_id="B1_CONFLICT",
                start_time="06:00",
                end_time="09:00",
                duration_hrs=3.0,
                window_index=0,
                passenger_conflicts={"SEC-NDLS-GZB": 2},  # 2 passenger trains passing
            ),
            BlockWindow(
                block_id="B2_CLEAR",
                start_time="13:00",
                end_time="16:00",
                duration_hrs=3.0,
                window_index=1,
                passenger_conflicts={"SEC-NDLS-GZB": 0},  # Clear window
            ),
        ]

        result = self.optimizer.optimize(tasks, blocks)

        self.assertEqual(result.scheduled_tasks[0].assigned_block, "B2_CLEAR")
        self.assertNotEqual(result.scheduled_tasks[0].assigned_block, "B1_CONFLICT")

    # --------------------------------------------------------------------------
    # Test 3: Freight Conflict Allowed with Soft Penalty
    # --------------------------------------------------------------------------
    def test_3_freight_conflict_soft_penalty(self):
        """Verify freight conflicts are permitted when no conflict-free block exists, incurring soft penalties."""
        tasks = [
            MaintenanceTask(
                task_id="T_FREIGHT",
                segment="SEC-GZB-ALJN",
                claimed_criticality="HIGH",
                min_duration_hrs=2.0,
                risk_30d=0.65,
            )
        ]
        # Only block available has 2 freight train conflicts
        blocks = [
            BlockWindow(
                block_id="B_FREIGHT_BLOCK",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,
                window_index=0,
                passenger_conflicts={"SEC-GZB-ALJN": 0},
                freight_conflicts={"SEC-GZB-ALJN": 2},  # 2 freight trains affected
            )
        ]

        result = self.optimizer.optimize(tasks, blocks)

        self.assertEqual(result.scheduled_tasks_count, 1)
        self.assertEqual(result.scheduled_tasks[0].assigned_block, "B_FREIGHT_BLOCK")
        self.assertEqual(result.scheduled_tasks[0].freight_conflict_count, 2)
        expected_penalty = 2 * self.config.WEIGHT_FREIGHT_CONFLICT_PENALTY
        self.assertEqual(result.scheduled_tasks[0].freight_penalty_score, expected_penalty)
        self.assertEqual(result.total_freight_trains_delayed, 2)

    # --------------------------------------------------------------------------
    # Test 4: High-Risk Critical Task Forced into Next Feasible Window
    # --------------------------------------------------------------------------
    def test_4_high_risk_critical_forced_next_feasible_window(self):
        """Verify task with risk_30d > 0.70 & CRITICAL is forced into the earliest feasible window."""
        tasks = [
            MaintenanceTask(
                task_id="T_EMERGENCY",
                segment="SEC-TDL-CNB",
                claimed_criticality="CRITICAL",
                min_duration_hrs=3.0,
                risk_30d=0.89,  # High risk > 0.70
            )
        ]
        # Window 0 (B1) has passenger conflict, Window 1 (B2) is feasible, Window 2 (B3) is later
        blocks = [
            BlockWindow(
                block_id="B1_BLOCKED",
                start_time="01:00",
                end_time="05:00",
                duration_hrs=4.0,
                window_index=0,
                passenger_conflicts={"SEC-TDL-CNB": 1},  # Passenger conflict
            ),
            BlockWindow(
                block_id="B2_EARLIEST_FEASIBLE",
                start_time="11:00",
                end_time="15:00",
                duration_hrs=4.0,
                window_index=1,
                passenger_conflicts={"SEC-TDL-CNB": 0},  # Next feasible window
            ),
            BlockWindow(
                block_id="B3_LATER",
                start_time="23:00",
                end_time="03:00",
                duration_hrs=4.0,
                window_index=2,
                passenger_conflicts={"SEC-TDL-CNB": 0},
            ),
        ]

        result = self.optimizer.optimize(tasks, blocks)

        # Must be assigned to B2 (window_index = 1, next feasible window)
        self.assertEqual(result.scheduled_tasks[0].assigned_block, "B2_EARLIEST_FEASIBLE")
        self.assertEqual(result.scheduled_tasks[0].window_index, 1)
        self.assertTrue(result.scheduled_tasks[0].is_high_risk_critical)

    # --------------------------------------------------------------------------
    # Test 5: Multiple Tasks on Different Segments Sharing a Block
    # --------------------------------------------------------------------------
    def test_5_multiple_tasks_different_segments_sharing_block(self):
        """Verify tasks on different segments can share the same block window simultaneously."""
        tasks = [
            MaintenanceTask(
                task_id="T_SEG_A",
                segment="SEC-NORTH",
                claimed_criticality="HIGH",
                min_duration_hrs=2.0,
                risk_30d=0.50,
            ),
            MaintenanceTask(
                task_id="T_SEG_B",
                segment="SEC-SOUTH",
                claimed_criticality="MEDIUM",
                min_duration_hrs=2.5,
                risk_30d=0.45,
            ),
        ]
        blocks = [
            BlockWindow(
                block_id="B_SHARED",
                start_time="02:00",
                end_time="06:00",
                duration_hrs=4.0,
                window_index=0,
            )
        ]

        result = self.optimizer.optimize(tasks, blocks)

        self.assertEqual(result.scheduled_tasks_count, 2)
        self.assertEqual(result.scheduled_tasks[0].assigned_block, "B_SHARED")
        self.assertEqual(result.scheduled_tasks[1].assigned_block, "B_SHARED")
        self.assertEqual(result.active_blocks_count, 1)

    # --------------------------------------------------------------------------
    # Test 6: Two Tasks on Same Segment NOT Sharing Same Block (Segment Exclusivity)
    # --------------------------------------------------------------------------
    def test_6_same_segment_conflict_exclusivity(self):
        """Verify two tasks on the SAME segment are NOT scheduled in the same block window."""
        tasks = [
            MaintenanceTask(
                task_id="T_SAME_1",
                segment="SEC-DELHI-YARD",
                claimed_criticality="HIGH",
                min_duration_hrs=2.0,
                risk_30d=0.60,
            ),
            MaintenanceTask(
                task_id="T_SAME_2",
                segment="SEC-DELHI-YARD",  # Same segment!
                claimed_criticality="MEDIUM",
                min_duration_hrs=2.0,
                risk_30d=0.40,
            ),
        ]
        blocks = [
            BlockWindow(
                block_id="B1",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,
                window_index=0,
            ),
            BlockWindow(
                block_id="B2",
                start_time="12:00",
                end_time="15:00",
                duration_hrs=3.0,
                window_index=1,
            ),
        ]

        result = self.optimizer.optimize(tasks, blocks)

        assigned_blocks = [t.assigned_block for t in result.scheduled_tasks]
        # Both must not have the same block
        self.assertNotEqual(assigned_blocks[0], assigned_blocks[1])
        self.assertSetEqual(set(assigned_blocks), {"B1", "B2"})

    # --------------------------------------------------------------------------
    # Test 7: Task Duration Exceeding Block Length Rejection (HARD constraint)
    # --------------------------------------------------------------------------
    def test_7_task_too_long_for_block(self):
        """Verify a task requiring 4.5 hrs cannot be scheduled in a 3.0 hr block."""
        tasks = [
            MaintenanceTask(
                task_id="T_LONG",
                segment="SEC-1",
                claimed_criticality="MEDIUM",
                min_duration_hrs=4.5,  # Requires 4.5 hours
                risk_30d=0.50,
            )
        ]
        blocks = [
            BlockWindow(
                block_id="B_SHORT",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,  # Only 3.0 hours available
                window_index=0,
            ),
            BlockWindow(
                block_id="B_LONG_ENOUGH",
                start_time="10:00",
                end_time="15:00",
                duration_hrs=5.0,  # 5.0 hours available
                window_index=1,
            ),
        ]

        result = self.optimizer.optimize(tasks, blocks)

        self.assertEqual(result.scheduled_tasks[0].assigned_block, "B_LONG_ENOUGH")
        self.assertNotEqual(result.scheduled_tasks[0].assigned_block, "B_SHORT")

    # --------------------------------------------------------------------------
    # Test 8: Unassignable Task Handling & Reporting
    # --------------------------------------------------------------------------
    def test_8_unassignable_task_reporting(self):
        """Verify an impossible task is marked UNASSIGNED with clear explanation and no crash."""
        tasks = [
            MaintenanceTask(
                task_id="T_IMPOSSIBLE",
                segment="SEC-HEAVY-TRAFFIC",
                claimed_criticality="LOW",
                min_duration_hrs=5.0,  # Requires 5 hrs
                risk_30d=0.20,
            )
        ]
        # All blocks are shorter than 5h or have passenger conflicts
        blocks = [
            BlockWindow(
                block_id="B1",
                start_time="01:00",
                end_time="03:00",
                duration_hrs=2.0,  # Too short
                window_index=0,
            ),
            BlockWindow(
                block_id="B2",
                start_time="12:00",
                end_time="16:00",
                duration_hrs=4.0,  # Too short (4h < 5h)
                window_index=1,
            ),
        ]

        result = self.optimizer.optimize(tasks, blocks)

        self.assertEqual(result.scheduled_tasks_count, 0)
        self.assertEqual(result.unassigned_tasks_count, 1)
        item = result.scheduled_tasks[0]
        self.assertEqual(item.status, "UNASSIGNED")
        self.assertIsNone(item.assigned_block)
        self.assertTrue("exceeds" in item.remarks.lower() or "insufficient duration" in item.remarks.lower())

    # --------------------------------------------------------------------------
    # Test 9: What-If Disruption Causing Re-Optimization
    # --------------------------------------------------------------------------
    def test_9_what_if_disruption_reoptimization(self):
        """Verify What-If engine injects emergency task, displaces lower priority tasks, and generates diff."""
        # Baseline tasks: Routine task T1 occupies B1
        tasks = [
            MaintenanceTask(
                task_id="T_ROUTINE",
                segment="SEC-NDLS-GZB",
                claimed_criticality="LOW",
                min_duration_hrs=2.0,
                risk_30d=0.15,
            )
        ]
        blocks = [
            BlockWindow(
                block_id="B1",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,
                window_index=0,
            ),
            BlockWindow(
                block_id="B2",
                start_time="12:00",
                end_time="15:00",
                duration_hrs=3.0,
                window_index=1,
            ),
        ]

        # Initial baseline: T_ROUTINE assigned to B1
        baseline = self.optimizer.optimize(tasks, blocks)
        self.assertEqual(baseline.scheduled_tasks[0].assigned_block, "B1")

        # Disruption: Sudden rail fracture emergency on same segment SEC-NDLS-GZB
        emergency_task = MaintenanceTask(
            task_id="T_EMERGENCY_FRACTURE",
            segment="SEC-NDLS-GZB",
            claimed_criticality="CRITICAL",
            min_duration_hrs=3.0,
            risk_30d=0.95,
        )

        scenario = DisruptionScenario(
            scenario_id="SCN-RAIL-FRACTURE-01",
            description="Sudden ultrasonic flaw detection alarm on NDLS-GZB line at 11:30",
            emergency_tasks=[emergency_task],
        )

        what_if_engine = WhatIfEngine(optimizer=self.optimizer)
        what_if_res = what_if_engine.evaluate_scenario(
            baseline_tasks=tasks,
            baseline_blocks=blocks,
            scenario=scenario,
            baseline_result=baseline,
        )

        self.assertIn(what_if_res.solver_status, ("OPTIMAL", "FEASIBLE"))
        self.assertGreaterEqual(what_if_res.affected_tasks_count, 1)

        # Emergency task must take B1 (earliest window)
        revised_tasks_map = {t.task_id: t for t in what_if_res.revised_schedule.scheduled_tasks}
        self.assertEqual(revised_tasks_map["T_EMERGENCY_FRACTURE"].assigned_block, "B1")
        # Routine task should be moved to B2 to make way for emergency
        self.assertEqual(revised_tasks_map["T_ROUTINE"].assigned_block, "B2")

    # --------------------------------------------------------------------------
    # Test 10: Multi-Horizon Weekly & Monthly Planning
    # --------------------------------------------------------------------------
    def test_10_multi_horizon_weekly_and_monthly_planning(self):
        """Verify 7-day weekly tactical and 30-day monthly strategic planning engines."""
        tasks = [
            MaintenanceTask(
                task_id="T_WK1",
                segment="SEC-1",
                claimed_criticality="HIGH",
                min_duration_hrs=2.0,
                risk_30d=0.75,
                day_index=1,
            ),
            MaintenanceTask(
                task_id="T_WK2",
                segment="SEC-1",
                claimed_criticality="MEDIUM",
                min_duration_hrs=2.5,
                risk_30d=0.45,
                day_index=5,
            ),
        ]
        blocks = [
            BlockWindow(
                block_id="B_D1",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,
                window_index=0,
                day_index=1,
            ),
            BlockWindow(
                block_id="B_D5",
                start_time="02:00",
                end_time="05:00",
                duration_hrs=3.0,
                window_index=1,
                day_index=5,
            ),
        ]

        weekly_res = generate_weekly_plan(tasks, blocks)
        self.assertEqual(weekly_res.horizon, "WEEKLY")
        self.assertEqual(weekly_res.schedule.scheduled_tasks_count, 2)
        self.assertIn(1, weekly_res.day_schedules)
        self.assertIn(5, weekly_res.day_schedules)

        monthly_res = generate_monthly_plan(tasks, blocks)
        self.assertEqual(monthly_res.horizon, "MONTHLY")
        self.assertEqual(monthly_res.schedule.scheduled_tasks_count, 2)
        self.assertIn("weekly_distribution", monthly_res.horizon_summary)


    # --------------------------------------------------------------------------
    # Test 11: Policy Presets & Pareto Frontier Exploration
    # --------------------------------------------------------------------------
    def test_11_policy_presets_and_pareto_frontier(self):
        """Verify Safety-First, Balanced, and Throughput-First presets and Pareto frontier outputs."""
        tasks = [
            MaintenanceTask(
                task_id="T_SAFETY",
                segment="SEC-A",
                claimed_criticality="CRITICAL",
                min_duration_hrs=3.0,
                risk_30d=0.85,
            ),
            MaintenanceTask(
                task_id="T_FREIGHT",
                segment="SEC-B",
                claimed_criticality="MEDIUM",
                min_duration_hrs=2.0,
                risk_30d=0.35,
            ),
        ]
        blocks = [
            BlockWindow(
                block_id="B1",
                start_time="01:00",
                end_time="05:00",
                duration_hrs=4.0,
                window_index=0,
                freight_conflicts={"SEC-A": 0, "SEC-B": 3},
            ),
            BlockWindow(
                block_id="B2",
                start_time="06:00",
                end_time="09:00",
                duration_hrs=3.0,
                window_index=1,
                freight_conflicts={"SEC-A": 0, "SEC-B": 0},
            ),
        ]

        pareto_res = compute_pareto_frontier(tasks, blocks)
        self.assertEqual(len(pareto_res.points), 3)

        preset_names = [p.preset_name for p in pareto_res.points]
        self.assertIn(PolicyPreset.SAFETY_FIRST, preset_names)
        self.assertIn(PolicyPreset.BALANCED, preset_names)
        self.assertIn(PolicyPreset.THROUGHPUT_FIRST, preset_names)

        # Safety-First should have highest or equal safety score
        safety_point = next(p for p in pareto_res.points if p.preset_name == PolicyPreset.SAFETY_FIRST)
        self.assertGreaterEqual(safety_point.safety_score, 80.0)

    # --------------------------------------------------------------------------
    # Test 12: Layer 1 Survival Curves & Monte Carlo Scenario Robustness (N=50)
    # --------------------------------------------------------------------------
    def test_12_layer1_survival_curves_and_monte_carlo_robustness(self):
        """Verify N=50 failure-time scenario simulation and Robustness % computation."""
        # Test Weibull derivation
        scale, shape = SurvivalCurveModel.derive_weibull_parameters(risk_30d=0.80, claimed_criticality="CRITICAL")
        self.assertGreater(scale, 0)
        self.assertGreater(shape, 1.0)

        tasks = [
            MaintenanceTask(
                task_id="T_ROB_1",
                segment="SEC-ROB-1",
                claimed_criticality="CRITICAL",
                min_duration_hrs=2.0,
                risk_30d=0.90,
            ),
            MaintenanceTask(
                task_id="T_ROB_2",
                segment="SEC-ROB-2",
                claimed_criticality="LOW",
                min_duration_hrs=2.0,
                risk_30d=0.20,
            ),
        ]
        blocks = [
            BlockWindow(
                block_id="B1",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,
                window_index=0,
                day_index=0,
            )
        ]

        rob_res = evaluate_scenario_robustness(tasks, blocks, num_scenarios=50, planning_horizon_days=7)

        self.assertEqual(rob_res.total_scenarios, 50)
        self.assertEqual(len(rob_res.scenario_evaluations), 50)
        self.assertGreaterEqual(rob_res.robustness_percentage, 0.0)
        self.assertLessEqual(rob_res.robustness_percentage, 100.0)
        self.assertGreaterEqual(rob_res.failure_prevention_rate, 0.0)

    # --------------------------------------------------------------------------
    # Test 13: Plan B Contingency Repository (Top-5 Disruption Fallback)
    # --------------------------------------------------------------------------
    def test_13_plan_b_contingency_repository(self):
        """Verify Top-5 disruption contingency precomputation and lookup."""
        tasks = [
            MaintenanceTask(
                task_id="T_CONT_1",
                segment="SEC-MAIN",
                claimed_criticality="HIGH",
                min_duration_hrs=2.0,
                risk_30d=0.70,
            )
        ]
        blocks = [
            BlockWindow(
                block_id="B_CONT_1",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,
                window_index=0,
            ),
            BlockWindow(
                block_id="B_CONT_2",
                start_time="06:00",
                end_time="09:00",
                duration_hrs=3.0,
                window_index=1,
            ),
        ]

        plan_b_repo = generate_plan_b_contingencies(tasks, blocks)
        self.assertEqual(len(plan_b_repo.contingencies), 5)

        # Test lookup by ID
        plan1 = plan_b_repo.get_plan("SCN-01-RAIL-FRACTURE")
        self.assertIsNotNone(plan1)
        self.assertIn("FRACTURE", plan1.disruption_id)
        self.assertIn(plan1.revised_schedule.solver_status, ("OPTIMAL", "FEASIBLE"))
        self.assertIsNotNone(plan1.reason_why)

    # --------------------------------------------------------------------------
    # Test 14: Fast Re-Optimization Under 5 Seconds
    # --------------------------------------------------------------------------
    def test_14_fast_reoptimization_under_5_seconds(self):
        """Verify injected disruption re-optimization executes in under 5 seconds with explainable diffs."""
        import time


        tasks = [
            MaintenanceTask(
                task_id="T_FAST_1",
                segment="SEC-FAST",
                claimed_criticality="MEDIUM",
                min_duration_hrs=2.0,
                risk_30d=0.50,
            )
        ]
        blocks = [
            BlockWindow(
                block_id="B1",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,
                window_index=0,
            ),
            BlockWindow(
                block_id="B2",
                start_time="05:00",
                end_time="08:00",
                duration_hrs=3.0,
                window_index=1,
            ),
        ]

        disruption = {
            "scenario_id": "SCN-FAST-01",
            "description": "Emergency rail defect",
            "emergency_tasks": [
                {
                    "task_id": "T_EMERGENCY",
                    "segment": "SEC-FAST",
                    "claimed_criticality": "CRITICAL",
                    "min_duration_hrs": 2.0,
                    "risk_30d": 0.99,
                }
            ],
        }

        t_start = time.time()
        fast_res = reoptimize_fast(tasks, blocks, disruption)
        runtime = time.time() - t_start

        # Verification: Guaranteed < 5.0 seconds
        self.assertLess(runtime, 5.0, f"Re-optimization took {runtime:.3f}s, expected < 5.0s")
        self.assertIn(fast_res.solver_status, ("OPTIMAL", "FEASIBLE"))
        self.assertGreaterEqual(fast_res.affected_tasks_count, 1)

        # Verify explainable diffs ("what changed" and "why")
        for affected in fast_res.affected_tasks:
            self.assertIn(affected.change_type, ("NEWLY_SCHEDULED", "RESCHEDULED", "DISPLACED_UNASSIGNED", "UNCHANGED"))
            self.assertTrue(len(affected.reason) > 0)

    # --------------------------------------------------------------------------
    # Test 15: Locked Task-to-Block Assignment Enforcement (Hard Constraint)
    # --------------------------------------------------------------------------
    def test_15_locked_assignments_enforcement(self):
        """
        Verify that locked_assignments is strictly enforced as a CP-SAT hard constraint.
        A task pinned/locked to a block MUST NOT be displaced, even when a higher-priority
        emergency task arrives on the same track segment.
        """
        tasks = [
            MaintenanceTask(
                task_id="T_LOCKED_CREW",
                segment="SEC-LOCKED-01",
                claimed_criticality="LOW",
                min_duration_hrs=2.0,
                risk_30d=0.20,
            )
        ]
        blocks = [
            BlockWindow(
                block_id="BLK-FIXED-01",
                start_time="01:00",
                end_time="04:00",
                duration_hrs=3.0,
                window_index=0,
            ),
            BlockWindow(
                block_id="BLK-FIXED-02",
                start_time="05:00",
                end_time="08:00",
                duration_hrs=3.0,
                window_index=1,
            ),
        ]

        # 1. Baseline optimization places T_LOCKED_CREW in BLK-FIXED-01
        baseline = self.optimizer.optimize(tasks, blocks)
        self.assertEqual(baseline.scheduled_tasks[0].assigned_block, "BLK-FIXED-01")

        # 2. Inject emergency task on SAME segment that would normally displace T_LOCKED_CREW
        emergency_task = MaintenanceTask(
            task_id="T_EMERGENCY_HIGH_PRIORITY",
            segment="SEC-LOCKED-01",
            claimed_criticality="CRITICAL",
            min_duration_hrs=2.0,
            risk_30d=0.99,
        )

        scenario = DisruptionScenario(
            scenario_id="SCN-LOCK-TEST",
            description="Emergency injection with locked baseline crew",
            emergency_tasks=[emergency_task],
            locked_assignments={"T_LOCKED_CREW": "BLK-FIXED-01"},  # Strictly locked to BLK-FIXED-01
        )

        what_if_engine = WhatIfEngine(optimizer=self.optimizer)
        what_if_res = what_if_engine.evaluate_scenario(
            baseline_tasks=tasks,
            baseline_blocks=blocks,
            scenario=scenario,
            baseline_result=baseline,
        )

        self.assertIn(what_if_res.solver_status, ("OPTIMAL", "FEASIBLE"))
        revised_map = {t.task_id: t for t in what_if_res.revised_schedule.scheduled_tasks}

        # Verification: Locked task MUST remain in BLK-FIXED-01
        self.assertEqual(revised_map["T_LOCKED_CREW"].assigned_block, "BLK-FIXED-01")
        self.assertEqual(revised_map["T_LOCKED_CREW"].status, "SCHEDULED")

        # Emergency task is scheduled in the next available feasible window (BLK-FIXED-02)
        # without violating track exclusivity on SEC-LOCKED-01 in BLK-FIXED-01
        self.assertEqual(revised_map["T_EMERGENCY_HIGH_PRIORITY"].assigned_block, "BLK-FIXED-02")
        self.assertEqual(revised_map["T_EMERGENCY_HIGH_PRIORITY"].status, "SCHEDULED")

    # --------------------------------------------------------------------------
    # Test 16: Layer 1 ML Metadata Preservation & Empirical Robustness
    # --------------------------------------------------------------------------
    def test_16_layer1_ml_metadata_and_empirical_robustness(self):
        """Verify that MaintenanceTask safely carries ML metadata and passes empirical curves to robustness."""
        empirical_curve = [
            {"day": d, "survival_probability": max(0.01, 1.0 - (d * 0.03))}
            for d in range(1, 31)
        ]
        task = MaintenanceTask(
            task_id="TASK-ML-01",
            segment="SEC-ML-001",
            claimed_criticality="HIGH",
            min_duration_hrs=2.5,
            risk_30d=0.85,
            expected_downtime_days=4.2,
            overrun_probability=0.15,
            confidence="high",
            cold_start_fallback=False,
            survival_curve=empirical_curve,
        )
        self.assertEqual(task.expected_downtime_days, 4.2)
        self.assertEqual(task.overrun_probability, 0.15)
        self.assertEqual(task.confidence, "high")
        self.assertEqual(task.cold_start_fallback, False)
        self.assertEqual(len(task.survival_curve), 30)

        # Verify monthly planning computes expected downtime metrics
        block = BlockWindow(
            block_id="BLK-ML-01",
            start_time="01:00",
            end_time="05:00",
            duration_hrs=4.0,
            window_index=0,
        )
        planner = MultiHorizonPlanner(optimizer=self.optimizer)
        monthly_res = planner.generate_monthly_plan(tasks=[task], blocks=[block])
        self.assertIn("total_expected_downtime_days", monthly_res.horizon_summary)
        self.assertEqual(monthly_res.horizon_summary["total_expected_downtime_days"], 4.2)
        self.assertEqual(monthly_res.horizon_summary["prevented_downtime_days"], 4.2)

        # Verify robustness engine samples from empirical survival curve
        rob_engine = ScenarioRobustnessEngine(num_scenarios=20, seed=42)
        rob_res = rob_engine.evaluate_plan_robustness(
            tasks=[task],
            blocks=[block],
            schedule_result=monthly_res.schedule,
            planning_horizon_days=30,
        )
        self.assertEqual(rob_res.total_scenarios, 20)
        self.assertGreaterEqual(rob_res.robustness_percentage, 0.0)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print(" " * 20 + "RUNNING RAILSYNC LAYER 3 OPTIMIZATION TESTS")
    print("=" * 80)
    unittest.main(verbosity=2)
