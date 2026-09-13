"""
optimizer.py - RailSync Layer 3 CP-SAT Optimization Engine
==========================================================
Part of the RailSync Project (AI-Powered Automatic Block Planning & Digital Twin for Indian Railways).

This module assigns track maintenance tasks to optimal maintenance block windows
using Google OR-Tools CP-SAT (Constraint Programming with Satisfiability).

Key Constraints Implemented:
---------------------------
1. At most one block window per task (or unassigned if unfeasible).
2. One task per segment per block window (HARD constraint).
   Tasks on different segments may share the same block window.
3. Task minimum duration must fit inside block duration (HARD constraint).
4. Passenger train conflicts are strictly forbidden (HARD constraint).
5. Freight train conflicts are allowed but penalized (SOFT penalty).
6. High-risk critical tasks (risk_30d > 0.7 & CRITICAL/HIGH) MUST be scheduled
   within their next feasible maintenance window (HARD constraint).

Objectives:
-----------
- Maximize track asset availability / minimize unused maintenance block capacity.
- Prioritize tasks using criticality, urgency, and 30-day failure risk.
- Minimize the number of separate active maintenance blocks (bundling/consolidation).
- Minimize freight train delays.
- Honor department-preferred block windows where feasible.
- Minimize unassigned tasks.
"""

import json
import os
import time
from typing import List, Dict, Any, Optional

try:
    from ortools.sat.python import cp_model
except ImportError:
    raise ImportError(
        "Google OR-Tools is required for RailSync Optimizer. "
        "Please install it via: pip install ortools"
    )

try:
    from .config import OptimizerConfig, DEFAULT_CONFIG
    from .models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ScheduledTaskResult,
        BlockSummaryResult,
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
except (ImportError, ValueError):
    from config import OptimizerConfig, DEFAULT_CONFIG
    from models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ScheduledTaskResult,
        BlockSummaryResult,
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


class RailSyncOptimizer:
    """
    Modular CP-SAT Optimization Engine for Indian Railways Maintenance Block Scheduling.

    Can be initialized with custom `OptimizerConfig` and called with lists of
    `MaintenanceTask` and `BlockWindow` objects or raw Python dictionaries.
    """

    def __init__(self, config: Optional[OptimizerConfig] = None):
        """
        Initialize the optimizer with a configuration instance.

        Parameters:
        -----------
        config : Optional[OptimizerConfig]
            Configuration containing weights, thresholds, and solver settings.
            If None, uses DEFAULT_CONFIG.
        """
        self.config = config or DEFAULT_CONFIG

    def optimize(
        self,
        tasks: List[MaintenanceTask],
        blocks: List[BlockWindow],
        locked_assignments: Optional[Dict[str, str]] = None,
    ) -> OptimizationResult:
        """
        Execute CP-SAT optimization to schedule maintenance tasks into block windows.

        Parameters:
        -----------
        tasks : List[MaintenanceTask]
            List of maintenance tasks requiring scheduling.
        blocks : List[BlockWindow]
            List of available track possession/maintenance block windows.
        locked_assignments : Optional[Dict[str, str]]
            Optional mapping of task_id -> block_id for tasks that are pinned/locked
            to a specific block window (e.g. ongoing work or strict operational commitments).

        Returns:
        --------
        OptimizationResult
            Structured result containing assignment details, train impacts,
            solver status, and block utilization statistics.
        """
        start_time = time.time()
        cfg = self.config

        # Step 1: Create the CP-SAT Model
        model = cp_model.CpModel()

        # ----------------------------------------------------------------------
        # Step 2: Define Decision Variables
        # ----------------------------------------------------------------------
        # x[t, b] = 1 if task t is assigned to block window b, else 0
        x: Dict[tuple, cp_model.IntVar] = {}
        for t in tasks:
            for b in blocks:
                x[(t.task_id, b.block_id)] = model.NewBoolVar(f"x_{t.task_id}_{b.block_id}")

        # unassigned[t] = 1 if task t cannot be assigned to any block window
        unassigned: Dict[str, cp_model.IntVar] = {}
        for t in tasks:
            unassigned[t.task_id] = model.NewBoolVar(f"unassigned_{t.task_id}")

        # block_active[b] = 1 if at least one task is scheduled in block b
        block_active: Dict[str, cp_model.IntVar] = {}
        for b in blocks:
            block_active[b.block_id] = model.NewBoolVar(f"active_{b.block_id}")

        # ----------------------------------------------------------------------
        # Step 3: Implement Hard Constraints
        # ----------------------------------------------------------------------

        # Constraint 1: Task Assignment Constraint (At most one block per task)
        # Each task is assigned to AT MOST ONE block window, or marked unassigned
        for t in tasks:
            model.Add(
                sum(x[(t.task_id, b.block_id)] for b in blocks) + unassigned[t.task_id] == 1
            )

        # Constraint 2: One Task Per Segment Per Block (HARD)
        # Prevents multiple maintenance tasks on the same physical track segment
        # during the same maintenance block window. Tasks on DIFFERENT segments
        # can share the same block window.
        segments = set(t.segment for t in tasks)
        for b in blocks:
            for seg in segments:
                tasks_on_seg = [t for t in tasks if t.segment == seg]
                if tasks_on_seg:
                    model.Add(
                        sum(x[(t.task_id, b.block_id)] for t in tasks_on_seg) <= 1
                    )

        # Constraint 3: Duration Fit Constraint (HARD)
        # A task cannot be scheduled in a block window shorter than its required duration
        for t in tasks:
            for b in blocks:
                if t.min_duration_hrs > b.duration_hrs:
                    # Enforce that x[t, b] MUST be 0
                    model.Add(x[(t.task_id, b.block_id)] == 0)

        # Constraint 4: Passenger Train Conflict Constraint (HARD)
        # If a block window causes passenger train conflicts on a segment,
        # NO maintenance task on that segment may be assigned to this block.
        # Indian Railways Passenger safety & punctuality are strictly non-negotiable.
        for t in tasks:
            for b in blocks:
                if b.has_passenger_conflict(t.segment):
                    model.Add(x[(t.task_id, b.block_id)] == 0)
                # Check segment restriction if block has explicit allowed_segments list
                if b.allowed_segments is not None and t.segment not in b.allowed_segments:
                    model.Add(x[(t.task_id, b.block_id)] == 0)

        # Constraint 5: Block Activation Linking Constraint
        # Links block_active[b] variable with individual task assignments:
        # block_active[b] == 1 if and only if sum(x[t, b]) >= 1
        for b in blocks:
            for t in tasks:
                model.Add(block_active[b.block_id] >= x[(t.task_id, b.block_id)])

            model.Add(
                block_active[b.block_id] <= sum(x[(t.task_id, b.block_id)] for t in tasks)
            )

        # Constraint 6: High-Risk Critical Task Next Feasible Window (HARD Constraint)
        # If risk_30d > 0.70 AND claimed_criticality in ("CRITICAL", "HIGH"),
        # the task MUST be scheduled within its next (earliest) feasible maintenance window.
        # Feasible window = window with sufficient duration and zero passenger conflicts.
        if cfg.ENFORCE_STRICT_HIGH_RISK_NEXT_WINDOW:
            for t in tasks:
                if t.is_high_risk_critical(cfg.HIGH_RISK_THRESHOLD):
                    feasible_candidate_blocks = [
                        b for b in blocks
                        if t.min_duration_hrs <= b.duration_hrs
                        and not b.has_passenger_conflict(t.segment)
                        and (b.allowed_segments is None or t.segment in b.allowed_segments)
                    ]

                    if feasible_candidate_blocks:
                        # Find earliest feasible window index
                        min_feasible_idx = min(b.window_index for b in feasible_candidate_blocks)

                        # Account for potential same-segment contention from other high-risk tasks or locked tasks
                        same_seg_high_risk_higher_priority = [
                            other for other in tasks
                            if other.task_id != t.task_id
                            and other.segment == t.segment
                            and other.is_high_risk_critical(cfg.HIGH_RISK_THRESHOLD)
                            and (
                                other.risk_30d > t.risk_30d
                                or (other.risk_30d == t.risk_30d and other.task_id < t.task_id)
                            )
                        ]
                        same_seg_locked_occupations = [
                            locked_b for locked_t, locked_b in (locked_assignments or {}).items()
                            if locked_t != t.task_id
                            and any(other.task_id == locked_t and other.segment == t.segment for other in tasks)
                        ]
                        allowed_window_max = (
                            min_feasible_idx
                            + len(same_seg_high_risk_higher_priority)
                            + len(same_seg_locked_occupations)
                        )

                        # Hard restriction: forbid placing in any window strictly later than next feasible window
                        for b in blocks:
                            if b.window_index > allowed_window_max:
                                model.Add(x[(t.task_id, b.block_id)] == 0)


        # Constraint 7: Locked Task-to-Block Assignments (HARD Constraint)
        # Tasks with locked assignments (e.g. work already underway or strictly pinned)
        # MUST remain assigned to their specified block window during re-optimization.
        if locked_assignments:
            task_id_set = {t.task_id for t in tasks}
            block_id_set = {b.block_id for b in blocks}
            for task_id, locked_block_id in locked_assignments.items():
                if task_id in task_id_set and locked_block_id in block_id_set:
                    model.Add(x[(task_id, locked_block_id)] == 1)


        # ----------------------------------------------------------------------
        # Step 4: Build Objective Function (Weighted Multi-Objective Optimization)
        # ----------------------------------------------------------------------
        # Minimizing Total Cost = Penalties - Rewards (Integer-scaled for CP-SAT)
        objective_terms = []
        crit_map = cfg.CRITICALITY_PRIORITY_MAP or {
            "CRITICAL": 10,
            "HIGH": 7,
            "MEDIUM": 4,
            "LOW": 1,
        }

        for t in tasks:
            crit_score = crit_map.get(t.claimed_criticality.upper(), 1)
            risk_int = int(t.risk_30d * 100)
            is_high_risk = t.is_high_risk_critical(cfg.HIGH_RISK_THRESHOLD)

            # --- (A) Unassigned Task Penalty ---
            # Base penalty for not performing a maintenance task
            base_unassigned_pen = (
                cfg.WEIGHT_UNASSIGNED_TASK_BASE_PENALTY
                + (crit_score * 500)
                + (risk_int * 50)
            )
            # Severe penalty if high-risk critical task is not scheduled
            if is_high_risk:
                base_unassigned_pen += cfg.WEIGHT_UNASSIGNED_HIGH_RISK_PENALTY

            objective_terms.append(unassigned[t.task_id] * base_unassigned_pen)

            # --- (B) Window Delay & Assignment Penalties ---
            for b in blocks:
                # 1. Window Index Delay Penalty (Urgency & Prioritization)
                # Drives solver to schedule urgent tasks into earlier available windows
                urgency_multiplier = crit_score + (risk_int // 10)
                if is_high_risk:
                    urgency_multiplier *= 3

                delay_cost = b.window_index * cfg.WEIGHT_WINDOW_DELAY_PENALTY * urgency_multiplier
                if delay_cost > 0:
                    objective_terms.append(x[(t.task_id, b.block_id)] * delay_cost)

                # 2. Freight Train Delay Penalty (SOFT PENALTY)
                # Freight trains can be looped/delayed, but incur operational penalty
                freight_count = b.get_freight_conflict_count(t.segment)
                if freight_count > 0:
                    freight_cost = freight_count * cfg.WEIGHT_FREIGHT_CONFLICT_PENALTY
                    objective_terms.append(x[(t.task_id, b.block_id)] * freight_cost)

                # 3. Unused Block Capacity Penalty (Asset Availability)
                # Penalizes unused capacity in the block to ensure tight task-window packing
                unused_cap = max(0.0, b.duration_hrs - t.min_duration_hrs)
                unused_cap_cost = int(unused_cap * cfg.WEIGHT_UNUSED_BLOCK_CAPACITY_PENALTY)
                if unused_cap_cost > 0:
                    objective_terms.append(x[(t.task_id, b.block_id)] * unused_cap_cost)

                # 4. Preferred Window Reward (Bonus / Negative Penalty)
                if t.preferred_window and t.preferred_window == b.block_id:
                    objective_terms.append(
                        x[(t.task_id, b.block_id)] * (-cfg.WEIGHT_PREFERRED_WINDOW_BONUS)
                    )

        # --- (C) Block Consolidation / Minimization Penalty ---
        # Penalizes activating separate blocks, promoting bundling of tasks
        for b in blocks:
            objective_terms.append(
                block_active[b.block_id] * cfg.WEIGHT_BLOCK_ACTIVATION_PENALTY
            )

        # Set the unified objective in CP-SAT model
        model.Minimize(sum(objective_terms))

        # ----------------------------------------------------------------------
        # Step 5: Solve the CP-SAT Model
        # ----------------------------------------------------------------------
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = cfg.SOLVER_TIMEOUT_SECONDS
        solver.parameters.num_search_workers = cfg.SOLVER_WORKERS
        solver.parameters.log_search_progress = cfg.LOG_SOLVER_PROGRESS

        status = solver.Solve(model)
        elapsed_seconds = time.time() - start_time
        status_name = solver.StatusName(status)

        # ----------------------------------------------------------------------
        # Step 6: Process and Format Optimization Output
        # ----------------------------------------------------------------------
        scheduled_tasks: List[ScheduledTaskResult] = []
        block_summaries: List[BlockSummaryResult] = []

        total_freight_delayed = 0
        active_blocks_count = 0
        scheduled_count = 0
        unassigned_count = 0

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Process tasks
            for t in tasks:
                is_unassigned_val = bool(solver.Value(unassigned[t.task_id]))
                is_high_risk = t.is_high_risk_critical(cfg.HIGH_RISK_THRESHOLD)

                if is_unassigned_val:
                    unassigned_count += 1
                    # Detailed reason analysis
                    reasons = []
                    dur_blocked = all(t.min_duration_hrs > b.duration_hrs for b in blocks)
                    pass_blocked = all(b.has_passenger_conflict(t.segment) for b in blocks)

                    if dur_blocked:
                        reasons.append(f"Task duration ({t.min_duration_hrs}h) exceeds all available block windows")
                    elif pass_blocked:
                        reasons.append(
                            f"Passenger train conflicts on segment {t.segment} in all candidate blocks (HARD)"
                        )
                    elif all(
                        b.has_passenger_conflict(t.segment) or t.min_duration_hrs > b.duration_hrs for b in blocks
                    ):
                        reasons.append("All candidate blocks have passenger train conflicts or insufficient duration")
                    else:
                        reasons.append("Segment capacity contention or cost trade-off prevented scheduling")

                    if is_high_risk:
                        reasons.insert(0, "High-risk safety critical task could not find feasible conflict-free window")

                    scheduled_tasks.append(
                        ScheduledTaskResult(
                            task_id=t.task_id,
                            assigned_block=None,
                            segment=t.segment,
                            duration_hrs=t.min_duration_hrs,
                            claimed_criticality=t.claimed_criticality,
                            risk_30d=t.risk_30d,
                            is_high_risk_critical=is_high_risk,
                            window_index=None,
                            freight_conflict_count=0,
                            freight_penalty_score=0.0,
                            status="UNASSIGNED",
                            remarks="; ".join(reasons),
                        )
                    )
                else:
                    scheduled_count += 1
                    # Find assigned block
                    assigned_blk_id = None
                    assigned_blk = None
                    for b in blocks:
                        if solver.Value(x[(t.task_id, b.block_id)]) == 1:
                            assigned_blk_id = b.block_id
                            assigned_blk = b
                            break

                    freight_conf = assigned_blk.get_freight_conflict_count(t.segment) if assigned_blk else 0
                    total_freight_delayed += freight_conf
                    freight_pen = freight_conf * cfg.WEIGHT_FREIGHT_CONFLICT_PENALTY

                    remarks = f"Assigned to {assigned_blk_id} (Window #{assigned_blk.window_index})"
                    if is_high_risk and assigned_blk:
                        remarks += (
                            f" - High-risk safety critical task scheduled in next "
                            f"feasible window (#{assigned_blk.window_index})"
                        )
                    if freight_conf > 0:
                        remarks += f" - Soft penalty applied for {freight_conf} freight delay(s)"

                    scheduled_tasks.append(
                        ScheduledTaskResult(
                            task_id=t.task_id,
                            assigned_block=assigned_blk_id,
                            segment=t.segment,
                            duration_hrs=t.min_duration_hrs,
                            claimed_criticality=t.claimed_criticality,
                            risk_30d=t.risk_30d,
                            is_high_risk_critical=is_high_risk,
                            window_index=assigned_blk.window_index if assigned_blk else None,
                            freight_conflict_count=freight_conf,
                            freight_penalty_score=float(freight_pen),
                            status="SCHEDULED",
                            remarks=remarks,
                        )
                    )

            # Process block summaries
            for b in blocks:
                is_active = bool(solver.Value(block_active[b.block_id]))
                if is_active:
                    active_blocks_count += 1

                tasks_in_blk = [
                    t for t in tasks
                    if solver.Value(x[(t.task_id, b.block_id)]) == 1
                ]
                task_ids = [t.task_id for t in tasks_in_blk]
                segments_used = list(set(t.segment for t in tasks_in_blk))

                # Max duration utilized by any segment in this block
                max_duration_used = max([t.min_duration_hrs for t in tasks_in_blk], default=0.0)
                unused = max(0.0, b.duration_hrs - max_duration_used) if is_active else b.duration_hrs

                blk_freight_delays = sum(
                    b.get_freight_conflict_count(t.segment) for t in tasks_in_blk
                )

                block_summaries.append(
                    BlockSummaryResult(
                        block_id=b.block_id,
                        window_index=b.window_index,
                        duration_hrs=b.duration_hrs,
                        is_utilized=is_active,
                        assigned_tasks=task_ids,
                        segments_blocked=segments_used,
                        total_freight_delays=blk_freight_delays,
                        utilized_hours_max=max_duration_used,
                        unused_capacity_hrs=unused,
                        unused_hours=unused,
                    )
                )

            obj_val = float(solver.ObjectiveValue())
        else:
            obj_val = -1.0
            # Model infeasible or failed
            for t in tasks:
                scheduled_tasks.append(
                    ScheduledTaskResult(
                        task_id=t.task_id,
                        assigned_block=None,
                        segment=t.segment,
                        duration_hrs=t.min_duration_hrs,
                        claimed_criticality=t.claimed_criticality,
                        risk_30d=t.risk_30d,
                        is_high_risk_critical=t.is_high_risk_critical(cfg.HIGH_RISK_THRESHOLD),
                        window_index=None,
                        freight_conflict_count=0,
                        freight_penalty_score=0.0,
                        status="UNASSIGNED",
                        remarks=f"Optimization solver returned status: {status_name}",
                    )
                )
            unassigned_count = len(tasks)

        return OptimizationResult(
            solver_status=status_name,
            total_tasks=len(tasks),
            scheduled_tasks_count=scheduled_count,
            unassigned_tasks_count=unassigned_count,
            active_blocks_count=active_blocks_count,
            total_freight_trains_delayed=total_freight_delayed,
            solver_run_time_seconds=round(elapsed_seconds, 4),
            objective_value=obj_val,
            scheduled_tasks=scheduled_tasks,
            block_summaries=block_summaries,
        )

    def reoptimize_with_disruption(
        self,
        tasks: List[MaintenanceTask],
        blocks: List[BlockWindow],
        disruption: DisruptionScenario,
        baseline_result: Optional[OptimizationResult] = None,
    ) -> WhatIfResult:
        """
        Runs what-if dynamic re-optimization for an operational disruption scenario.

        Parameters:
        -----------
        tasks : List[MaintenanceTask]
            Baseline list of maintenance tasks.
        blocks : List[BlockWindow]
            Baseline list of block windows.
        disruption : DisruptionScenario
            Disruption details (emergency tasks, cancelled blocks, modified conflicts).
        baseline_result : Optional[OptimizationResult]
            Pre-computed baseline result (optional).

        Returns:
        --------
        WhatIfResult
            Detailed diff showing reassigned tasks, changed blocks, and revised schedule.
        """
        try:
            from .what_if import WhatIfEngine
        except (ImportError, ValueError):
            from what_if import WhatIfEngine

        engine = WhatIfEngine(optimizer=self)
        return engine.evaluate_scenario(
            baseline_tasks=tasks,
            baseline_blocks=blocks,
            scenario=disruption,
            baseline_result=baseline_result,
            config=self.config,
        )

    # --------------------------------------------------------------------------
    # Helper Integration Methods (For Backend Teammates)
    # --------------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: Optional[OptimizerConfig] = None) -> OptimizationResult:
        """
        Convenience method to run optimization directly from a Python dictionary.

        Expected dictionary format:
        {
            "tasks": [ { "task_id": ..., "segment": ..., ... }, ... ],
            "blocks": [ { "block_id": ..., "duration_hrs": ..., ... }, ... ]
        }
        """
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

        optimizer = cls(config=config)
        return optimizer.optimize(tasks=tasks, blocks=blocks)

    @classmethod
    def from_json_file(cls, filepath: str, config: Optional[OptimizerConfig] = None) -> OptimizationResult:
        """Convenience method to load sample JSON file and run optimization."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data, config=config)


# ==============================================================================
# Public Clean Integration Functions (For Backend Teammates)
# ==============================================================================

def optimize_schedule(
    tasks: Any,
    blocks: Any,
    config: Optional[OptimizerConfig] = None,
) -> OptimizationResult:
    """
    Main team integration entry point for RailSync Layer 3 Maintenance Block Optimization.

    Accepts:
    --------
    tasks : List[MaintenanceTask] or List[Dict[str, Any]]
        List of maintenance task objects or raw Python dictionaries.
    blocks : List[BlockWindow] or List[Dict[str, Any]]
        List of candidate block window objects or raw Python dictionaries.
    config : Optional[OptimizerConfig]
        Custom objective weights / thresholds (uses DEFAULT_CONFIG if None).

    Returns:
    --------
    OptimizationResult
        Complete schedule result containing solver status, task assignments,
        freight penalties, block utilization, and unassigned diagnostics.
        Call .to_dict() on the result for a JSON-serializable dictionary.
    """
    parsed_tasks: List[MaintenanceTask] = []
    for item in tasks:
        if isinstance(item, MaintenanceTask):
            parsed_tasks.append(item)
        elif isinstance(item, dict):
            parsed_tasks.append(
                MaintenanceTask(
                    task_id=str(item["task_id"]),
                    segment=str(item["segment"]),
                    claimed_criticality=str(item["claimed_criticality"]),
                    min_duration_hrs=float(item["min_duration_hrs"]),
                    risk_30d=float(item["risk_30d"]),
                    preferred_window=item.get("preferred_window"),
                    description=item.get("description", ""),
                )
            )
        else:
            raise TypeError(f"Expected MaintenanceTask or dict, got {type(item).__name__}")

    parsed_blocks: List[BlockWindow] = []
    for idx, item in enumerate(blocks):
        if isinstance(item, BlockWindow):
            parsed_blocks.append(item)
        elif isinstance(item, dict):
            parsed_blocks.append(
                BlockWindow(
                    block_id=str(item["block_id"]),
                    start_time=str(item.get("start_time", "")),
                    end_time=str(item.get("end_time", "")),
                    duration_hrs=float(item["duration_hrs"]),
                    window_index=int(item.get("window_index", idx)),
                    passenger_conflicts=dict(item.get("passenger_conflicts", {})),
                    freight_conflicts=dict(item.get("freight_conflicts", {})),
                    allowed_segments=item.get("allowed_segments"),
                )
            )
        else:
            raise TypeError(f"Expected BlockWindow or dict, got {type(item).__name__}")

    optimizer = RailSyncOptimizer(config=config)
    return optimizer.optimize(tasks=parsed_tasks, blocks=parsed_blocks)


def what_if_reoptimize(
    tasks: Any,
    blocks: Any,
    disruption: Any,
    baseline_result: Optional[OptimizationResult] = None,
    config: Optional[OptimizerConfig] = None,
) -> WhatIfResult:
    """
    Integration entry point for dynamic what-if disruption evaluation and re-optimization.

    Accepts:
    --------
    tasks : List[MaintenanceTask] or List[Dict[str, Any]]
        Baseline maintenance tasks (objects or dicts).
    blocks : List[BlockWindow] or List[Dict[str, Any]]
        Baseline block windows (objects or dicts).
    disruption : DisruptionScenario or Dict[str, Any]
        Disruption details (emergency tasks, cancelled blocks, modified conflicts).
    baseline_result : Optional[OptimizationResult]
        Pre-computed baseline schedule result (optional).
    config : Optional[OptimizerConfig]
        Custom configuration settings (optional).

    Returns:
    --------
    WhatIfResult
        Comprehensive diff and revised schedule.
    """
    try:
        from .what_if import WhatIfEngine
    except (ImportError, ValueError):
        from what_if import WhatIfEngine

    if isinstance(disruption, dict):
        em_tasks_raw = disruption.get("emergency_tasks", [])
        em_tasks = [
            t if isinstance(t, MaintenanceTask) else MaintenanceTask(
                task_id=str(t["task_id"]),
                segment=str(t["segment"]),
                claimed_criticality=str(t["claimed_criticality"]),
                min_duration_hrs=float(t["min_duration_hrs"]),
                risk_30d=float(t["risk_30d"]),
                preferred_window=t.get("preferred_window"),
                description=t.get("description", ""),
            )
            for t in em_tasks_raw
        ]
        parsed_disruption = DisruptionScenario(
            scenario_id=str(disruption.get("scenario_id", "SCN-DYNAMIC")),
            description=str(disruption.get("description", "Dynamic operational disruption")),
            emergency_tasks=em_tasks,
            cancelled_blocks=list(disruption.get("cancelled_blocks", [])),
            modified_passenger_conflicts=dict(disruption.get("modified_passenger_conflicts", {})),
            modified_block_durations=dict(disruption.get("modified_block_durations", {})),
            locked_assignments=dict(disruption.get("locked_assignments", {})),
        )
    elif isinstance(disruption, DisruptionScenario):
        parsed_disruption = disruption
    else:
        raise TypeError(f"Expected DisruptionScenario or dict, got {type(disruption).__name__}")

    parsed_tasks: List[MaintenanceTask] = [
        t if isinstance(t, MaintenanceTask) else MaintenanceTask(
            task_id=str(t["task_id"]),
            segment=str(t["segment"]),
            claimed_criticality=str(t["claimed_criticality"]),
            min_duration_hrs=float(t["min_duration_hrs"]),
            risk_30d=float(t["risk_30d"]),
            preferred_window=t.get("preferred_window"),
            description=t.get("description", ""),
        )
        for t in tasks
    ]

    parsed_blocks: List[BlockWindow] = [
        b if isinstance(b, BlockWindow) else BlockWindow(
            block_id=str(b["block_id"]),
            start_time=str(b.get("start_time", "")),
            end_time=str(b.get("end_time", "")),
            duration_hrs=float(b["duration_hrs"]),
            window_index=int(b.get("window_index", idx)),
            passenger_conflicts=dict(b.get("passenger_conflicts", {})),
            freight_conflicts=dict(b.get("freight_conflicts", {})),
            allowed_segments=b.get("allowed_segments"),
        )
        for idx, b in enumerate(blocks)
    ]

    engine = WhatIfEngine(optimizer=RailSyncOptimizer(config=config))
    return engine.evaluate_scenario(
        baseline_tasks=parsed_tasks,
        baseline_blocks=parsed_blocks,
        scenario=parsed_disruption,
        baseline_result=baseline_result,
        config=config,
    )


def _parse_tasks_and_blocks(tasks: Any, blocks: Any) -> tuple:
    """Helper to parse raw dicts or objects into typed models."""
    parsed_tasks: List[MaintenanceTask] = [
        t if isinstance(t, MaintenanceTask) else MaintenanceTask(
            task_id=str(t["task_id"]),
            segment=str(t["segment"]),
            claimed_criticality=str(t["claimed_criticality"]),
            min_duration_hrs=float(t["min_duration_hrs"]),
            risk_30d=float(t["risk_30d"]),
            preferred_window=t.get("preferred_window"),
            description=t.get("description", ""),
            day_index=int(t.get("day_index", 0)),
            horizon=str(t.get("horizon", "WEEKLY")),
            weibull_lambda=float(t["weibull_lambda"]) if "weibull_lambda" in t and t["weibull_lambda"] is not None else None,
            weibull_k=float(t["weibull_k"]) if "weibull_k" in t and t["weibull_k"] is not None else None,
        )
        for t in tasks
    ]

    parsed_blocks: List[BlockWindow] = [
        b if isinstance(b, BlockWindow) else BlockWindow(
            block_id=str(b["block_id"]),
            start_time=str(b.get("start_time", "")),
            end_time=str(b.get("end_time", "")),
            duration_hrs=float(b["duration_hrs"]),
            window_index=int(b.get("window_index", idx)),
            passenger_conflicts=dict(b.get("passenger_conflicts", {})),
            freight_conflicts=dict(b.get("freight_conflicts", {})),
            allowed_segments=b.get("allowed_segments"),
            day_index=int(b.get("day_index", 0)),
            horizon=str(b.get("horizon", "WEEKLY")),
        )
        for idx, b in enumerate(blocks)
    ]
    return parsed_tasks, parsed_blocks


def generate_weekly_plan(
    tasks: Any,
    blocks: Any,
    config: Optional[OptimizerConfig] = None,
) -> MultiHorizonScheduleResult:
    """Generates a 7-day tactical operational maintenance schedule."""
    try:
        from .multi_horizon import MultiHorizonPlanner
    except (ImportError, ValueError):
        from multi_horizon import MultiHorizonPlanner

    p_tasks, p_blocks = _parse_tasks_and_blocks(tasks, blocks)
    planner = MultiHorizonPlanner()
    return planner.generate_weekly_plan(tasks=p_tasks, blocks=p_blocks, config=config)


def generate_monthly_plan(
    tasks: Any,
    blocks: Any,
    config: Optional[OptimizerConfig] = None,
) -> MultiHorizonScheduleResult:
    """Generates a 30-day master strategic maintenance schedule."""
    try:
        from .multi_horizon import MultiHorizonPlanner
    except (ImportError, ValueError):
        from multi_horizon import MultiHorizonPlanner

    p_tasks, p_blocks = _parse_tasks_and_blocks(tasks, blocks)
    planner = MultiHorizonPlanner()
    return planner.generate_monthly_plan(tasks=p_tasks, blocks=p_blocks, config=config)


def compute_pareto_frontier(
    tasks: Any,
    blocks: Any,
) -> ParetoFrontierResult:
    """Evaluates Safety-First, Balanced, and Throughput-First presets to produce Pareto frontier."""
    try:
        from .pareto import ParetoFrontierAnalyzer
    except (ImportError, ValueError):
        from pareto import ParetoFrontierAnalyzer

    p_tasks, p_blocks = _parse_tasks_and_blocks(tasks, blocks)
    analyzer = ParetoFrontierAnalyzer()
    return analyzer.evaluate_pareto_frontier(tasks=p_tasks, blocks=p_blocks)


def evaluate_scenario_robustness(
    tasks: Any,
    blocks: Any,
    schedule_result: Optional[OptimizationResult] = None,
    num_scenarios: int = 50,
    planning_horizon_days: int = 7,
) -> ScenarioRobustnessResult:
    """Evaluates scheduled plan against N=50 Monte Carlo failure scenarios sampled from Layer 1 survival curves."""
    try:
        from .robustness import ScenarioRobustnessEngine
    except (ImportError, ValueError):
        from robustness import ScenarioRobustnessEngine

    p_tasks, p_blocks = _parse_tasks_and_blocks(tasks, blocks)
    if schedule_result is None:
        opt = RailSyncOptimizer()
        schedule_result = opt.optimize(p_tasks, p_blocks)

    engine = ScenarioRobustnessEngine(num_scenarios=num_scenarios)
    return engine.evaluate_plan_robustness(
        tasks=p_tasks,
        blocks=p_blocks,
        schedule_result=schedule_result,
        planning_horizon_days=planning_horizon_days,
    )


def generate_plan_b_contingencies(
    tasks: Any,
    blocks: Any,
    baseline_result: Optional[OptimizationResult] = None,
    custom_scenarios: Optional[List[DisruptionScenario]] = None,
) -> PlanBRepository:
    """Precomputes and stores ready-to-dispatch revised fallback schedules for Top-5 disruptions."""
    try:
        from .contingency import ContingencyEngine
    except (ImportError, ValueError):
        from contingency import ContingencyEngine

    p_tasks, p_blocks = _parse_tasks_and_blocks(tasks, blocks)
    engine = ContingencyEngine()
    return engine.generate_plan_b_repository(
        tasks=p_tasks,
        blocks=p_blocks,
        baseline_result=baseline_result,
        custom_scenarios=custom_scenarios,
    )


def reoptimize_fast(
    tasks: Any,
    blocks: Any,
    disruption: Any,
    baseline_result: Optional[OptimizationResult] = None,
) -> WhatIfResult:
    """Fast re-optimization endpoint guaranteed < 5 seconds with explainable diffs (what changed and why)."""
    try:
        from .contingency import ContingencyEngine
    except (ImportError, ValueError):
        from contingency import ContingencyEngine

    p_tasks, p_blocks = _parse_tasks_and_blocks(tasks, blocks)
    engine = ContingencyEngine()

    if isinstance(disruption, dict):
        em_tasks_raw = disruption.get("emergency_tasks", [])
        em_tasks = [
            t if isinstance(t, MaintenanceTask) else MaintenanceTask(
                task_id=str(t["task_id"]),
                segment=str(t["segment"]),
                claimed_criticality=str(t["claimed_criticality"]),
                min_duration_hrs=float(t["min_duration_hrs"]),
                risk_30d=float(t["risk_30d"]),
                preferred_window=t.get("preferred_window"),
                description=t.get("description", ""),
            )
            for t in em_tasks_raw
        ]
        parsed_disruption = DisruptionScenario(
            scenario_id=str(disruption.get("scenario_id", "SCN-FAST-REOPT")),
            description=str(disruption.get("description", "Injected fast disruption")),
            emergency_tasks=em_tasks,
            cancelled_blocks=list(disruption.get("cancelled_blocks", [])),
            modified_passenger_conflicts=dict(disruption.get("modified_passenger_conflicts", {})),
            modified_block_durations=dict(disruption.get("modified_block_durations", {})),
            locked_assignments=dict(disruption.get("locked_assignments", {})),
        )
    elif isinstance(disruption, DisruptionScenario):
        parsed_disruption = disruption
    else:
        raise TypeError(f"Expected DisruptionScenario or dict, got {type(disruption).__name__}")

    return engine.reoptimize_fast(
        tasks=p_tasks,
        blocks=p_blocks,
        disruption=parsed_disruption,
        baseline_result=baseline_result,
    )




# ------------------------------------------------------------------------------
# Demonstration & CLI Execution
# ------------------------------------------------------------------------------
def print_schedule_table(result: OptimizationResult):
    """Prints a clean, formatted terminal table of the optimization results."""
    print("\n" + "=" * 95)
    print(" " * 25 + "RAILSYNC LAYER 3 OPTIMIZATION ENGINE")
    print(" " * 20 + "AI-Powered Automatic Block Planning (CP-SAT)")
    print("=" * 95)
    print(f"Solver Status        : {result.solver_status}")
    print(f"Solver Run Time      : {result.solver_run_time_seconds:.4f} seconds")
    print(f"Total Tasks          : {result.total_tasks}")
    print(f"Scheduled Tasks      : {result.scheduled_tasks_count}")
    print(f"Unassigned Tasks     : {result.unassigned_tasks_count}")
    print(f"Active Blocks Used   : {result.active_blocks_count}")
    print(f"Total Freight Impact : {result.total_freight_trains_delayed} train(s) delayed (Soft Penalty)")
    print(f"Objective Score      : {result.objective_value}")
    print("=" * 95)

    print("\n--- DETAILED TASK ASSIGNMENT SCHEDULE ---")
    header = (
        f"{'Task ID':<10} | {'Segment':<14} | {'Crit.':<9} | {'Risk_30d':<8} | "
        f"{'Dur(h)':<6} | {'Assigned Block':<14} | {'Freight Pen':<11} | {'Status'}"
    )
    print("-" * 95)
    print(header)
    print("-" * 95)

    for item in result.scheduled_tasks:
        assigned = item.assigned_block or "NONE"
        crit_display = item.claimed_criticality[:8]
        print(
            f"{item.task_id:<10} | {item.segment:<14} | {crit_display:<9} | {item.risk_30d:<8.2f} | "
            f"{item.duration_hrs:<6.1f} | {assigned:<14} | {item.freight_penalty_score:<11.0f} | {item.status}"
        )
    print("-" * 95)

    print("\n--- BLOCK WINDOW UTILIZATION SUMMARY ---")
    blk_header = (
        f"{'Block ID':<10} | {'Window #':<8} | {'Duration':<9} | "
        f"{'Utilized':<9} | {'Tasks Scheduled':<20} | {'Freight Delays'}"
    )
    print("-" * 95)
    print(blk_header)
    print("-" * 95)

    for b in result.block_summaries:
        tasks_str = ", ".join(b.assigned_tasks) if b.assigned_tasks else "None"
        print(
            f"{b.block_id:<10} | {b.window_index:<8} | {b.duration_hrs:<7.1f} h | "
            f"{str(b.is_utilized):<9} | {tasks_str:<20} | {b.total_freight_delays} trains"
        )
    print("=" * 95 + "\n")


if __name__ == "__main__":
    # Locate sample tasks json file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sample_file = os.path.join(current_dir, "data", "sample_tasks.json")

    if not os.path.exists(sample_file):
        # Fallback if running from workspace root
        sample_file = os.path.join(current_dir, "optimization", "data", "sample_tasks.json")

    print(f"Loading synthetic maintenance and block data from: {sample_file}")
    output = RailSyncOptimizer.from_json_file(sample_file)
    print_schedule_table(output)
