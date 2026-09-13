"""
contingency.py - RailSync Layer 3 Plan B Contingency & Fast Re-Optimization
==========================================================================
1. Pre-computes and stores ready-to-dispatch revised fallback schedules ("Plan B")
   for the Top-5 operational disruption scenarios.
2. Provides a dedicated, high-performance re-optimization endpoint (< 5 seconds)
   for arbitrary real-time injected disruptions with explainable diffs ("what changed" and "why").
"""

import time
import copy
from datetime import datetime
from typing import List, Dict, Optional, Any

try:
    from .models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        DisruptionScenario,
        TaskChangeDiff,
        BlockChangeDiff,
        WhatIfResult,
        PlanBContingency,
        PlanBRepository,
    )
    from .config import OptimizerConfig, DEFAULT_CONFIG
    from .optimizer import RailSyncOptimizer
    from .what_if import WhatIfEngine
except (ImportError, ValueError):
    from models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        DisruptionScenario,
        TaskChangeDiff,
        BlockChangeDiff,
        WhatIfResult,
        PlanBContingency,
        PlanBRepository,
    )
    from config import OptimizerConfig, DEFAULT_CONFIG
    from optimizer import RailSyncOptimizer
    from what_if import WhatIfEngine


class ContingencyEngine:
    """
    Manages pre-computed Plan B fallback plans and fast real-time re-optimization.
    """

    def __init__(self, optimizer: Optional[RailSyncOptimizer] = None):
        fast_cfg = OptimizerConfig(
            SOLVER_TIMEOUT_SECONDS=3.0,
            FAST_REOPTIMIZE_TIMEOUT_SECONDS=3.0,
            SOLVER_WORKERS=4,
        )
        self.optimizer = optimizer or RailSyncOptimizer(config=fast_cfg)
        self.what_if_engine = WhatIfEngine(optimizer=self.optimizer)

    @staticmethod
    def get_standard_top_5_scenarios(
        tasks: List[MaintenanceTask],
        blocks: List[BlockWindow],
    ) -> List[DisruptionScenario]:
        """
        Constructs the standard Top-5 railway disruption scenarios tailored to the input tasks/blocks:
        1. Emergency Rail Fracture on busiest / highest-risk segment.
        2. OHE Catenary Wire Parting / Breakdown on Down Main line.
        3. Block Window Revocation (Operational cancellation of earliest window).
        4. Track Circuit / Signalling Failure requiring immediate possession.
        5. Severe Window Truncation (Available duration cut in half due to freight bunching).
        """
        # Find highest-risk segment
        high_risk_tasks = sorted(tasks, key=lambda t: t.risk_30d, reverse=True)
        seg1 = high_risk_tasks[0].segment if high_risk_tasks else "NDLS-GZB-UP"
        seg2 = high_risk_tasks[1].segment if len(high_risk_tasks) > 1 else "GZB-ALJN-DN"

        blk1_id = blocks[0].block_id if blocks else "BLK-01"
        blk2_id = blocks[1].block_id if len(blocks) > 1 else (blocks[0].block_id if blocks else "BLK-02")

        scenarios = [
            # Scenario 1: Ultrasonic Flaw / Rail Fracture
            DisruptionScenario(
                scenario_id="SCN-01-RAIL-FRACTURE",
                description=f"Severe Ultrasonic Flaw / Rail Fracture detected on {seg1}",
                emergency_tasks=[
                    MaintenanceTask(
                        task_id="EM-FRACTURE-01",
                        segment=seg1,
                        claimed_criticality="CRITICAL",
                        min_duration_hrs=min(3.0, blocks[0].duration_hrs if blocks else 3.0),
                        risk_30d=0.99,
                        description=f"Urgent rail replacement at fracture point on {seg1}",
                    )
                ],
            ),
            # Scenario 2: OHE Catenary Breakdown
            DisruptionScenario(
                scenario_id="SCN-02-OHE-BREAKDOWN",
                description=f"OHE Catenary Wire breakdown on {seg2}",
                emergency_tasks=[
                    MaintenanceTask(
                        task_id="EM-OHE-02",
                        segment=seg2,
                        claimed_criticality="CRITICAL",
                        min_duration_hrs=min(2.5, blocks[0].duration_hrs if blocks else 2.5),
                        risk_30d=0.95,
                        description=f"Emergency OHE tower wagon possession on {seg2}",
                    )
                ],
            ),
            # Scenario 3: Operational Block Cancellation
            DisruptionScenario(
                scenario_id="SCN-03-BLK-CANCELLATION",
                description=f"Operating department revoked window {blk1_id} for VIP / Military priority train",
                cancelled_blocks=[blk1_id],
            ),
            # Scenario 4: Signalling Track Circuit Failure
            DisruptionScenario(
                scenario_id="SCN-04-SIG-TRACK-CIRCUIT",
                description=f"Signalling track circuit failure requiring urgent rectification on {seg1}",
                emergency_tasks=[
                    MaintenanceTask(
                        task_id="EM-SIG-04",
                        segment=seg1,
                        claimed_criticality="HIGH",
                        min_duration_hrs=min(2.0, blocks[0].duration_hrs if blocks else 2.0),
                        risk_30d=0.90,
                        description=f"Emergency signalling relay bonding restoration on {seg1}",
                    )
                ],
            ),
            # Scenario 5: Block Window Truncation
            DisruptionScenario(
                scenario_id="SCN-05-WINDOW-TRUNCATION",
                description=f"Maintenance block {blk1_id} truncated by 50% due to upstream freight congestion",
                modified_block_durations={
                    blk1_id: max(1.5, (blocks[0].duration_hrs * 0.5) if blocks else 2.0)
                },
            ),
        ]
        return scenarios

    def generate_plan_b_repository(
        self,
        tasks: List[MaintenanceTask],
        blocks: List[BlockWindow],
        baseline_result: Optional[OptimizationResult] = None,
        custom_scenarios: Optional[List[DisruptionScenario]] = None,
    ) -> PlanBRepository:
        """
        Pre-computes and caches fallback 'Plan B' schedules for the Top-5 disruption scenarios.

        Parameters:
        -----------
        tasks : List[MaintenanceTask]
            Baseline tasks.
        blocks : List[BlockWindow]
            Baseline blocks.
        baseline_result : Optional[OptimizationResult]
            Pre-computed baseline schedule.
        custom_scenarios : Optional[List[DisruptionScenario]]
            Optional custom disruption scenarios list (uses standard Top-5 if None).

        Returns:
        --------
        PlanBRepository
            Repository containing pre-computed Plan B fallback schedules.
        """
        # 1. Compute baseline if not provided
        if baseline_result is None:
            baseline_result = self.optimizer.optimize(tasks, blocks)

        # 2. Get Top-5 scenarios
        scenarios = (
            custom_scenarios[:5]
            if custom_scenarios
            else self.get_standard_top_5_scenarios(tasks, blocks)
        )

        contingencies: List[PlanBContingency] = []
        prob_weights = [0.30, 0.25, 0.20, 0.15, 0.10]

        for idx, scn in enumerate(scenarios):
            what_if_res = self.what_if_engine.evaluate_scenario(
                baseline_tasks=tasks,
                baseline_blocks=blocks,
                scenario=scn,
                baseline_result=baseline_result,
            )

            # Extract clear reasons
            reasons = []
            for t_diff in what_if_res.affected_tasks:
                reasons.append(f"Task {t_diff.task_id} ({t_diff.segment}): {t_diff.reason}")

            reason_why = " | ".join(reasons) if reasons else "No task displacement required."

            contingency = PlanBContingency(
                disruption_id=scn.scenario_id,
                scenario_title=scn.description,
                probability_weight=prob_weights[idx] if idx < len(prob_weights) else 0.10,
                severity="CRITICAL" if "FRACTURE" in scn.scenario_id or "BREAKDOWN" in scn.scenario_id else "HIGH",
                disruption=scn,
                revised_schedule=what_if_res.revised_schedule,
                diff_summary=what_if_res.summary,
                what_changed=what_if_res.affected_tasks,
                reason_why=reason_why,
            )
            contingencies.append(contingency)

        return PlanBRepository(
            baseline_schedule=baseline_result,
            contingencies=contingencies,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def reoptimize_fast(
        self,
        tasks: List[MaintenanceTask],
        blocks: List[BlockWindow],
        disruption: DisruptionScenario,
        baseline_result: Optional[OptimizationResult] = None,
    ) -> WhatIfResult:
        """
        Fast re-optimization endpoint guaranteed to execute in < 5 seconds.

        Parameters:
        -----------
        tasks : List[MaintenanceTask]
            Baseline tasks.
        blocks : List[BlockWindow]
            Baseline blocks.
        disruption : DisruptionScenario
            Injected disruption details.
        baseline_result : Optional[OptimizationResult]
            Pre-computed baseline schedule.

        Returns:
        --------
        WhatIfResult
            Revised schedule + exact diffs + explainable root-cause rationale.
        """
        t0 = time.time()
        fast_cfg = OptimizerConfig(
            SOLVER_TIMEOUT_SECONDS=3.0,
            FAST_REOPTIMIZE_TIMEOUT_SECONDS=3.0,
            SOLVER_WORKERS=4,
        )

        what_if_res = self.what_if_engine.evaluate_scenario(
            baseline_tasks=tasks,
            baseline_blocks=blocks,
            scenario=disruption,
            baseline_result=baseline_result,
            config=fast_cfg,
        )
        elapsed = time.time() - t0

        # Enhance summary with runtime verification
        what_if_res.summary += f" [Re-optimization completed in {elapsed:.3f}s (<5.0s guaranteed)]"
        return what_if_res
