"""
example_usage.py - RailSync Layer 3 Complete Suite Integration Demo
===================================================================
Demonstrates how backend teammates can call all 5 core Layer 3 capabilities:
1. Multi-Horizon Planning: Weekly Plan (7-Day) & Monthly Plan (30-Day)
2. 3 Policy Presets & Pareto Frontier (Safety-First, Balanced, Throughput-First)
3. Scenario Robustness Evaluation (N=50 Monte Carlo simulations from Layer 1 Survival Curves)
4. Pre-computed Plan B Contingency Repository (Top-5 Disruption Fallback Schedules)
5. Real-Time Fast Re-Optimization Endpoint (< 5.0 seconds) with Explainable Diffs

Usage:
    python optimization/example_usage.py
"""

import json
import os
import sys

# Ensure package root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from Optimization import (
        optimize_schedule,
        generate_weekly_plan,
        generate_monthly_plan,
        compute_pareto_frontier,
        evaluate_scenario_robustness,
        generate_plan_b_contingencies,
        reoptimize_fast,
    )

except ImportError:
    from optimizer import (
        optimize_schedule,
        generate_weekly_plan,
        generate_monthly_plan,
        compute_pareto_frontier,
        evaluate_scenario_robustness,
        generate_plan_b_contingencies,
        reoptimize_fast,
    )


def main():
    print("=" * 95)
    print(" " * 20 + "RAILSYNC LAYER 3: ADVANCED OPTIMIZATION SUITE")
    print(" " * 15 + "Automatic Block Planning, Robustness & Contingency Engine")
    print("=" * 95)

    # --------------------------------------------------------------------------
    # Synthetic Multi-Horizon Maintenance Tasks & Block Windows
    # --------------------------------------------------------------------------
    sample_tasks = [
        {
            "task_id": "TASK-101",
            "segment": "NDLS-GZB-UP",
            "claimed_criticality": "CRITICAL",
            "min_duration_hrs": 3.0,
            "risk_30d": 0.88,
            "preferred_window": "BLK-01",
            "day_index": 0,
            "description": "Ultrasonic flaw detection rail fracture risk near Sahibabad",
        },
        {
            "task_id": "TASK-102",
            "segment": "GZB-ALJN-DN",
            "claimed_criticality": "HIGH",
            "min_duration_hrs": 2.5,
            "risk_30d": 0.65,
            "preferred_window": "BLK-01",
            "day_index": 1,
            "description": "OHE catenary wire inspection and contact wire replacement",
        },
        {
            "task_id": "TASK-103",
            "segment": "NDLS-GZB-UP",
            "claimed_criticality": "MEDIUM",
            "min_duration_hrs": 2.0,
            "risk_30d": 0.40,
            "preferred_window": "BLK-02",
            "day_index": 2,
            "description": "Routine track circuit bonding renewal",
        },
        {
            "task_id": "TASK-104",
            "segment": "ALJN-TDL-UP",
            "claimed_criticality": "HIGH",
            "min_duration_hrs": 3.5,
            "risk_30d": 0.72,
            "day_index": 3,
            "description": "Turnout sleeper packing and machine tamping",
        },
        {
            "task_id": "TASK-105",
            "segment": "TDL-ETW-DN",
            "claimed_criticality": "LOW",
            "min_duration_hrs": 2.0,
            "risk_30d": 0.25,
            "day_index": 5,
            "description": "Cess clearance and drain desilting",
        },
    ]

    sample_blocks = [
        {
            "block_id": "BLK-01",
            "start_time": "2026-09-11 01:00",
            "end_time": "2026-09-11 05:00",
            "duration_hrs": 4.0,
            "window_index": 0,
            "day_index": 0,
            "passenger_conflicts": {"NDLS-GZB-UP": 0, "GZB-ALJN-DN": 0},
            "freight_conflicts": {"NDLS-GZB-UP": 1, "GZB-ALJN-DN": 0},
        },
        {
            "block_id": "BLK-02",
            "start_time": "2026-09-12 11:30",
            "end_time": "2026-09-12 14:30",
            "duration_hrs": 3.0,
            "window_index": 1,
            "day_index": 1,
            "passenger_conflicts": {"NDLS-GZB-UP": 0, "GZB-ALJN-DN": 0},
            "freight_conflicts": {"NDLS-GZB-UP": 0, "GZB-ALJN-DN": 1},
        },
        {
            "block_id": "BLK-03",
            "start_time": "2026-09-14 02:00",
            "end_time": "2026-09-14 06:00",
            "duration_hrs": 4.0,
            "window_index": 2,
            "day_index": 3,
            "passenger_conflicts": {"ALJN-TDL-UP": 0, "TDL-ETW-DN": 0},
            "freight_conflicts": {"ALJN-TDL-UP": 2, "TDL-ETW-DN": 0},
        },
        {
            "block_id": "BLK-04",
            "start_time": "2026-09-16 01:30",
            "end_time": "2026-09-16 04:30",
            "duration_hrs": 3.0,
            "window_index": 3,
            "day_index": 5,
            "passenger_conflicts": {"TDL-ETW-DN": 0},
            "freight_conflicts": {"TDL-ETW-DN": 0},
        },
    ]

    # --------------------------------------------------------------------------
    # 1. Multi-Horizon Planning: Weekly (7-Day) & Monthly (30-Day) Plans
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("1. MULTI-HORIZON PLANNING (WEEKLY & MONTHLY)")
    print("=" * 80)

    weekly_res = generate_weekly_plan(tasks=sample_tasks, blocks=sample_blocks)
    print(f"[Weekly Plan - 7 Days]")
    print(f"   • Scheduled Tasks       : {weekly_res.schedule.scheduled_tasks_count}/{weekly_res.schedule.total_tasks}")
    print(f"   • High Risk Resolution  : {weekly_res.horizon_summary['high_risk_completion_rate']}")
    print(f"   • Active Blocks Used    : {weekly_res.schedule.active_blocks_count}")
    print(f"   • Freight Impact        : {weekly_res.schedule.total_freight_trains_delayed} trains delayed")

    monthly_res = generate_monthly_plan(tasks=sample_tasks, blocks=sample_blocks)
    print(f"\n[Monthly Master Plan - 30 Days]")
    print(f"   • Asset Availability    : {monthly_res.horizon_summary['network_asset_availability_ratio'] * 100:.1f}%")
    print(f"   • Weekly Distribution   : {monthly_res.horizon_summary['weekly_distribution']}")

    # --------------------------------------------------------------------------
    # 2. 3 Policy Presets & Pareto Frontier
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("2. 3 POLICY PRESETS & PARETO FRONTIER EXPLORATION")
    print("=" * 80)

    pareto_res = compute_pareto_frontier(tasks=sample_tasks, blocks=sample_blocks)
    print(f"{'Policy Preset':<18} | {'Safety Score':<14} | {'Freight Delays':<16} | {'Active Blocks':<14} | {'Runtime'}")
    print("-" * 80)
    for pt in pareto_res.points:
        print(
            f"{pt.preset_name:<18} | {pt.safety_score:<14.1f} | {pt.freight_trains_delayed:<16} | "
            f"{pt.active_blocks:<14} | {pt.runtime_seconds:.4f}s"
        )
    print(f"\nSummary: {pareto_res.summary}")

    # --------------------------------------------------------------------------
    # 3. Scenario Robustness Evaluation (N=50 Monte Carlo Simulations)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("3. SCENARIO ROBUSTNESS ENGINE (LAYER 1 SURVIVAL CURVES, N=50 SCENARIOS)")
    print("=" * 80)

    robustness_res = evaluate_scenario_robustness(
        tasks=sample_tasks,
        blocks=sample_blocks,
        schedule_result=weekly_res.schedule,
        num_scenarios=50,
        planning_horizon_days=7,
    )
    print(f"   • Total Scenarios Simulated : {robustness_res.total_scenarios}")
    print(f"   • Feasible Scenarios Survived : {robustness_res.feasible_scenarios_count}")
    print(f"   • Robustness Score           : {robustness_res.robustness_percentage:.1f}%")
    print(f"   • Failure Prevention Rate    : {robustness_res.failure_prevention_rate:.1f}% ({robustness_res.failures_prevented_count}/{robustness_res.total_simulated_failures})")
    print(f"   • Most Vulnerable Segments   : {', '.join(robustness_res.vulnerable_assets) if robustness_res.vulnerable_assets else 'None (Fully Protected)'}")

    # --------------------------------------------------------------------------
    # 4. Plan B Contingency Repository (Top-5 Precomputed Disruption Plans)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("4. PLAN B CONTINGENCY REPOSITORY (TOP-5 PRECOMPUTED DISRUPTIONS)")
    print("=" * 80)

    plan_b_repo = generate_plan_b_contingencies(
        tasks=sample_tasks,
        blocks=sample_blocks,
        baseline_result=weekly_res.schedule,
    )
    print(f"Generated at: {plan_b_repo.generated_at} | Pre-computed plans: {len(plan_b_repo.contingencies)}")
    print("-" * 80)
    for c in plan_b_repo.contingencies:
        print(f"• [{c.disruption_id}] ({c.severity}) {c.scenario_title}")
        print(f"  Fallback Diff: {c.diff_summary}")
        print(f"  Root Cause   : {c.reason_why[:90]}...")
        print()

    # --------------------------------------------------------------------------
    # 5. Real-Time Fast Re-Optimization Endpoint (< 5 seconds)
    # --------------------------------------------------------------------------
    print("=" * 80)
    print("5. FAST RE-OPTIMIZATION ENDPOINT (< 5 SECONDS GUARANTEED)")
    print("=" * 80)

    injected_disruption = {
        "scenario_id": "SCN-LIVE-EMERGENCY",
        "description": "Sudden rail fracture detected at Sahibabad Yard on NDLS-GZB-UP",
        "emergency_tasks": [
            {
                "task_id": "TASK-LIVE-EMERGENCY-01",
                "segment": "NDLS-GZB-UP",
                "claimed_criticality": "CRITICAL",
                "min_duration_hrs": 3.0,
                "risk_30d": 0.99,
                "description": "Emergency rail weld repair requiring immediate next window",
            }
        ],
    }

    print("Injecting real-time disruption into reoptimize_fast()...")
    fast_reopt_res = reoptimize_fast(
        tasks=sample_tasks,
        blocks=sample_blocks,
        disruption=injected_disruption,
        baseline_result=weekly_res.schedule,
    )

    print(f"   • Solver Status      : {fast_reopt_res.solver_status}")
    print(f"   • Affected Tasks     : {fast_reopt_res.affected_tasks_count}")
    print(f"   • Summary & Latency  : {fast_reopt_res.summary}")
    print("\n   • WHAT CHANGED & WHY:")
    for t_diff in fast_reopt_res.affected_tasks:
        print(f"     - Task {t_diff.task_id} on {t_diff.segment}: {t_diff.change_type} -> {t_diff.reason}")
    print("=" * 95 + "\n")


if __name__ == "__main__":
    main()
