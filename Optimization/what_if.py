"""
what_if.py - RailSync Layer 3 What-If Re-Optimization Engine
============================================================
Provides dynamic re-optimization and scenario evaluation for operational disruptions,
such as sudden track defects, rail fractures, emergency tasks, block cancellations,
or passenger train path modifications.

Returns clear diffs showing:
- Revised schedule
- Affected tasks (original vs new assigned block, reason for change)
- Changed blocks (activated, deactivated, modified)
- Solver status and execution metrics
"""

import copy
from typing import List, Optional

try:
    from .models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        DisruptionScenario,
        TaskChangeDiff,
        BlockChangeDiff,
        WhatIfResult,
    )
    from .config import OptimizerConfig
    from .optimizer import RailSyncOptimizer
except (ImportError, ValueError):
    from models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        DisruptionScenario,
        TaskChangeDiff,
        BlockChangeDiff,
        WhatIfResult,
    )
    from config import OptimizerConfig
    from optimizer import RailSyncOptimizer


class WhatIfEngine:
    """
    Evaluates dynamic disruptions and performs re-optimization against a baseline schedule.
    """

    def __init__(self, optimizer: Optional[RailSyncOptimizer] = None):
        """
        Parameters:
        -----------
        optimizer : Optional[RailSyncOptimizer]
            Optimizer instance to use. If None, creates one with DEFAULT_CONFIG.
        """
        self.optimizer = optimizer or RailSyncOptimizer()

    def evaluate_scenario(
        self,
        baseline_tasks: List[MaintenanceTask],
        baseline_blocks: List[BlockWindow],
        scenario: DisruptionScenario,
        baseline_result: Optional[OptimizationResult] = None,
        config: Optional[OptimizerConfig] = None,
    ) -> WhatIfResult:
        """
        Applies a disruption scenario, re-runs CP-SAT optimization, and computes
        the exact differences between the baseline and revised schedules.

        Parameters:
        -----------
        baseline_tasks : List[MaintenanceTask]
            Original list of maintenance tasks.
        baseline_blocks : List[BlockWindow]
            Original list of available block windows.
        scenario : DisruptionScenario
            Disruption details (emergency tasks, cancelled blocks, altered conflicts).
        baseline_result : Optional[OptimizationResult]
            Pre-computed baseline result. If None, will run baseline optimization first.
        config : Optional[OptimizerConfig]
            Custom config for re-optimization.

        Returns:
        --------
        WhatIfResult
            Comprehensive diff and revised schedule.
        """
        active_optimizer = self.optimizer
        if config is not None:
            active_optimizer = RailSyncOptimizer(config=config)

        # 1. Compute baseline schedule if not provided
        if baseline_result is None:
            baseline_result = active_optimizer.optimize(
                tasks=copy.deepcopy(baseline_tasks),
                blocks=copy.deepcopy(baseline_blocks),
            )

        # 2. Build revised task list (incorporating emergency tasks)
        revised_tasks = [copy.deepcopy(t) for t in baseline_tasks]
        emergency_task_ids = set()
        for em_task in scenario.emergency_tasks:
            # If task exists, replace it; otherwise append
            existing_idx = next(
                (i for i, t in enumerate(revised_tasks) if t.task_id == em_task.task_id),
                None,
            )
            if existing_idx is not None:
                revised_tasks[existing_idx] = copy.deepcopy(em_task)
            else:
                revised_tasks.append(copy.deepcopy(em_task))
            emergency_task_ids.add(em_task.task_id)

        # 3. Build revised block list (applying cancellations, conflict changes, duration changes)
        revised_blocks: List[BlockWindow] = []
        for b in baseline_blocks:
            # Skip cancelled blocks
            if b.block_id in scenario.cancelled_blocks:
                continue

            b_copy = copy.deepcopy(b)

            # Apply modified durations
            if b.block_id in scenario.modified_block_durations:
                b_copy.duration_hrs = scenario.modified_block_durations[b.block_id]

            # Apply modified passenger conflicts
            if b.block_id in scenario.modified_passenger_conflicts:
                for seg, count in scenario.modified_passenger_conflicts[b.block_id].items():
                    b_copy.passenger_conflicts[seg] = count

            revised_blocks.append(b_copy)

        # 4. Re-optimize with CP-SAT
        revised_result = active_optimizer.optimize(
            tasks=revised_tasks,
            blocks=revised_blocks,
            locked_assignments=scenario.locked_assignments,
        )


        # 5. Compute Task Diffs
        baseline_task_map = {t.task_id: t for t in baseline_result.scheduled_tasks}
        revised_task_map = {t.task_id: t for t in revised_result.scheduled_tasks}

        affected_tasks: List[TaskChangeDiff] = []

        all_task_ids = list(
            dict.fromkeys(list(baseline_task_map.keys()) + list(revised_task_map.keys()))
        )

        for tid in all_task_ids:
            base_item = baseline_task_map.get(tid)
            rev_item = revised_task_map.get(tid)

            if base_item is None and rev_item is not None:
                # Newly injected emergency task
                change_type = "NEWLY_SCHEDULED" if rev_item.status == "SCHEDULED" else "UNASSIGNED"
                reason = f"Emergency task injected: {rev_item.remarks}"
                affected_tasks.append(
                    TaskChangeDiff(
                        task_id=tid,
                        segment=rev_item.segment,
                        original_block=None,
                        new_block=rev_item.assigned_block,
                        change_type=change_type,
                        reason=reason,
                    )
                )
            elif base_item is not None and rev_item is not None:
                orig_blk = base_item.assigned_block
                new_blk = rev_item.assigned_block

                if orig_blk != new_blk:
                    if new_blk is None:
                        change_type = "DISPLACED_UNASSIGNED"
                        reason = f"Displaced from {orig_blk} due to disruption constraints: {rev_item.remarks}"
                    elif orig_blk is None:
                        change_type = "RESCHEDULED"
                        reason = f"Previously unassigned, now scheduled into {new_blk}"
                    else:
                        change_type = "RESCHEDULED"
                        reason = (
                            f"Moved from {orig_blk} to {new_blk} to accommodate emergency priority/conflicts"
                        )

                    affected_tasks.append(
                        TaskChangeDiff(
                            task_id=tid,
                            segment=rev_item.segment,
                            original_block=orig_blk,
                            new_block=new_blk,
                            change_type=change_type,
                            reason=reason,
                        )
                    )

        # 6. Compute Block Diffs
        baseline_blk_map = {b.block_id: b for b in baseline_result.block_summaries}
        revised_blk_map = {b.block_id: b for b in revised_result.block_summaries}

        all_blk_ids = list(
            dict.fromkeys(
                list(baseline_blk_map.keys()) + list(revised_blk_map.keys()) + scenario.cancelled_blocks
            )
        )

        changed_blocks: List[BlockChangeDiff] = []
        for bid in all_blk_ids:
            base_b = baseline_blk_map.get(bid)
            rev_b = revised_blk_map.get(bid)

            base_tasks = base_b.assigned_tasks if base_b else []
            rev_tasks = rev_b.assigned_tasks if rev_b else []

            tasks_added = [t for t in rev_tasks if t not in base_tasks]
            tasks_removed = [t for t in base_tasks if t not in rev_tasks]

            if bid in scenario.cancelled_blocks:
                status_change = "DEACTIVATED"
            elif base_b and not base_b.is_utilized and rev_b and rev_b.is_utilized:
                status_change = "ACTIVATED"
            elif base_b and base_b.is_utilized and rev_b and not rev_b.is_utilized:
                status_change = "DEACTIVATED"
            elif tasks_added or tasks_removed:
                status_change = "MODIFIED"
            else:
                status_change = "UNCHANGED"

            if status_change != "UNCHANGED" or tasks_added or tasks_removed:
                changed_blocks.append(
                    BlockChangeDiff(
                        block_id=bid,
                        original_task_count=len(base_tasks),
                        new_task_count=len(rev_tasks),
                        tasks_added=tasks_added,
                        tasks_removed=tasks_removed,
                        status_change=status_change,
                    )
                )

        # 7. Generate concise summary
        summary = (
            f"Scenario '{scenario.scenario_id}' evaluated ({scenario.description}). "
            f"Solver status: {revised_result.solver_status}. "
            f"Affected tasks: {len(affected_tasks)}, Modified blocks: {len(changed_blocks)}."
        )

        return WhatIfResult(
            scenario_id=scenario.scenario_id,
            description=scenario.description,
            solver_status=revised_result.solver_status,
            affected_tasks_count=len(affected_tasks),
            affected_tasks=affected_tasks,
            changed_blocks=changed_blocks,
            baseline_schedule=baseline_result,
            revised_schedule=revised_result,
            summary=summary,
        )


def print_what_if_table(result: WhatIfResult):
    """Utility to pretty-print what-if comparison to console."""
    print("\n" + "=" * 95)
    print(" " * 25 + f"WHAT-IF RE-OPTIMIZATION: {result.scenario_id}")
    print("=" * 95)
    print(f"Description        : {result.description}")
    print(f"Revised Status     : {result.solver_status}")
    print(f"Affected Tasks     : {result.affected_tasks_count}")
    print(f"Summary            : {result.summary}")
    print("=" * 95)

    if result.affected_tasks:
        print("\n--- AFFECTED TASK REASSIGNMENTS ---")
        header = (
            f"{'Task ID':<10} | {'Segment':<14} | {'Original Block':<16} | "
            f"{'New Block':<14} | {'Change Type':<18} | {'Reason'}"
        )
        print("-" * 95)
        print(header)
        print("-" * 95)
        for t in result.affected_tasks:
            orig = t.original_block or "UNASSIGNED"
            new = t.new_block or "UNASSIGNED"
            print(
                f"{t.task_id:<10} | {t.segment:<14} | {orig:<16} | {new:<14} | "
                f"{t.change_type:<18} | {t.reason[:30]}"
            )
        print("-" * 95)

    if result.changed_blocks:
        print("\n--- CHANGED BLOCK POSSESSIONS ---")
        b_header = (
            f"{'Block ID':<10} | {'Status Change':<14} | "
            f"{'Tasks Added':<20} | {'Tasks Removed':<20}"
        )
        print("-" * 95)
        print(b_header)
        print("-" * 95)
        for b in result.changed_blocks:
            added = ", ".join(b.tasks_added) if b.tasks_added else "None"
            removed = ", ".join(b.tasks_removed) if b.tasks_removed else "None"
            print(f"{b.block_id:<10} | {b.status_change:<14} | {added:<20} | {removed:<20}")
        print("=" * 95 + "\n")


if __name__ == "__main__":
    import os
    import json

    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_file = os.path.join(current_dir, "data", "sample_tasks.json")
    if not os.path.exists(sample_file):
        sample_file = os.path.join(current_dir, "optimization", "data", "sample_tasks.json")

    print(f"Running baseline schedule from: {sample_file}")
    with open(sample_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    tasks = [
        MaintenanceTask(
            task_id=item["task_id"],
            segment=item["segment"],
            claimed_criticality=item["claimed_criticality"],
            min_duration_hrs=float(item["min_duration_hrs"]),
            risk_30d=float(item["risk_30d"]),
            preferred_window=item.get("preferred_window"),
            description=item.get("description", ""),
        )
        for item in data.get("tasks", [])
    ]

    blocks = [
        BlockWindow(
            block_id=item["block_id"],
            start_time=item.get("start_time", ""),
            end_time=item.get("end_time", ""),
            duration_hrs=float(item["duration_hrs"]),
            window_index=int(item.get("window_index", idx)),
            passenger_conflicts=item.get("passenger_conflicts", {}),
            freight_conflicts=item.get("freight_conflicts", {}),
            allowed_segments=item.get("allowed_segments"),
        )
        for idx, item in enumerate(data.get("blocks", []))
    ]

    engine = WhatIfEngine()

    # Simulate a sudden track defect on NDLS-GZB-UP at 11:30 requiring emergency catenary/rail repair
    disruption = DisruptionScenario(
        scenario_id="SCN-EMERGENCY-01",
        description="Emergency Ultrasonic Flaw Alarm at Sahibabad (NDLS-GZB-UP) at 11:30",
        emergency_tasks=[
            MaintenanceTask(
                task_id="TSK-EMERGENCY-999",
                segment="NDLS-GZB-UP",
                claimed_criticality="CRITICAL",
                min_duration_hrs=3.0,
                risk_30d=0.98,
                description="Emergency weld defect repair requiring immediate next window access",
            )
        ],
    )

    what_if_output = engine.evaluate_scenario(
        baseline_tasks=tasks,
        baseline_blocks=blocks,
        scenario=disruption,
    )

    print_what_if_table(what_if_output)
