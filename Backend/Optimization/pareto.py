"""
pareto.py - RailSync Layer 3 Policy Presets & Pareto Frontier Analyzer
======================================================================
Evaluates maintenance scheduling across 3 distinct operational policies:
1. Safety-First: Maximizes safety urgency and ensures zero deferral of high-risk tasks.
2. Balanced: Balances safety risk, freight throughput, and capacity utilization.
3. Throughput-First: Prioritizes freight traffic punctuality and tight block bundling.

Constructs the Pareto frontier displaying trade-offs between safety risk, freight delay,
and asset utilization.
"""

from typing import List, Optional, Dict, Any

try:
    from .models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ParetoPoint,
        ParetoFrontierResult,
        PolicyPreset,
    )
    from .config import OptimizerConfig
    from .optimizer import RailSyncOptimizer
except (ImportError, ValueError):
    from models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ParetoPoint,
        ParetoFrontierResult,
        PolicyPreset,
    )
    from config import OptimizerConfig
    from optimizer import RailSyncOptimizer


class ParetoFrontierAnalyzer:
    """
    Computes multi-policy optimization results and analyzes the Pareto frontier.
    """

    @staticmethod
    def _calculate_safety_score(result: OptimizationResult, tasks: List[MaintenanceTask]) -> float:
        """
        Calculates normalized safety score (0 to 100) based on scheduled vs unassigned risk.
        100 = All high-risk and critical tasks scheduled in earliest windows.
        """
        task_map = {t.task_id: t for t in tasks}
        total_risk_weight = 0.0
        mitigated_risk_weight = 0.0

        for st in result.scheduled_tasks:
            orig = task_map.get(st.task_id)
            if not orig:
                continue

            # Weight by risk and criticality
            weight = orig.risk_30d * (3.0 if orig.is_high_risk_critical(0.65) else 1.0)
            total_risk_weight += weight

            if st.status == "SCHEDULED":
                # Earlier windows yield higher mitigation score
                w_idx = st.window_index if st.window_index is not None else 0
                delay_factor = max(0.2, 1.0 - (0.15 * w_idx))
                mitigated_risk_weight += weight * delay_factor

        if total_risk_weight == 0:
            return 100.0

        score = (mitigated_risk_weight / total_risk_weight) * 100.0
        return max(0.0, min(100.0, score))

    def evaluate_pareto_frontier(
        self,
        tasks: List[MaintenanceTask],
        blocks: List[BlockWindow],
    ) -> ParetoFrontierResult:
        """
        Evaluates the 3 policy presets (Safety-First, Balanced, Throughput-First)
        and constructs the comparative Pareto frontier.

        Parameters:
        -----------
        tasks : List[MaintenanceTask]
            List of tasks to schedule.
        blocks : List[BlockWindow]
            Available block windows.

        Returns:
        --------
        ParetoFrontierResult
            Pareto frontier points, metrics, and policy comparison summary.
        """
        presets = [
            (PolicyPreset.SAFETY_FIRST, OptimizerConfig.safety_first()),
            (PolicyPreset.BALANCED, OptimizerConfig.balanced()),
            (PolicyPreset.THROUGHPUT_FIRST, OptimizerConfig.throughput_first()),
        ]

        points: List[ParetoPoint] = []

        for preset_name, cfg in presets:
            opt = RailSyncOptimizer(config=cfg)
            res = opt.optimize(tasks=tasks, blocks=blocks)

            safety_score = self._calculate_safety_score(res, tasks)

            point = ParetoPoint(
                preset_name=preset_name,
                safety_score=safety_score,
                freight_trains_delayed=res.total_freight_trains_delayed,
                active_blocks=res.active_blocks_count,
                scheduled_tasks=res.scheduled_tasks_count,
                unassigned_tasks=res.unassigned_tasks_count,
                runtime_seconds=res.solver_run_time_seconds,
                objective_value=res.objective_value,
                schedule=res,
            )
            points.append(point)

        summary = (
            f"Evaluated 3 Policy Presets across {len(tasks)} tasks: "
            f"Safety-First (Safety: {points[0].safety_score:.1f}%, Freight Delays: {points[0].freight_trains_delayed}), "
            f"Balanced (Safety: {points[1].safety_score:.1f}%, Freight Delays: {points[1].freight_trains_delayed}), "
            f"Throughput-First (Safety: {points[2].safety_score:.1f}%, Freight Delays: {points[2].freight_trains_delayed})."
        )

        return ParetoFrontierResult(
            points=points,
            recommended_preset=PolicyPreset.BALANCED,
            summary=summary,
        )
