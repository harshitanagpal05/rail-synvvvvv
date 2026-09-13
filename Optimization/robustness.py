"""
robustness.py - RailSync Layer 3 Scenario Robustness Engine
===========================================================
Performs Monte Carlo scenario evaluations (N=50 failure-time scenarios)
sampled from Layer 1 Survival Curves S(t).

Evaluates whether scheduled maintenance blocks execute before simulated
asset failure times, computing the overall Robustness % and identifying
vulnerable track segments and assets.
"""

import math
import random
from typing import List, Dict, Optional, Tuple, Any

try:
    from .models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ScenarioEvaluation,
        ScenarioRobustnessResult,
    )
except (ImportError, ValueError):
    from models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ScenarioEvaluation,
        ScenarioRobustnessResult,
    )


class SurvivalCurveModel:
    """
    Mathematical model for Layer 1 asset survival curves.
    Uses Weibull / Exponential survival probability: S(t) = exp(-(t / lambda)^k)
    where t is time in days, lambda is characteristic life (scale), and k is shape factor.
    """

    @staticmethod
    def derive_weibull_parameters(
        risk_30d: float,
        claimed_criticality: str = "MEDIUM",
        shape_k: float = 2.0,
    ) -> Tuple[float, float]:
        """
        Derives Weibull (scale lambda, shape k) from 30-day failure risk score.
        S(30) = 1 - risk_30d = exp(-(30 / lambda)^k) => lambda = 30 / (-ln(1 - risk_30d))^(1/k)
        """
        # Clamp risk to avoid mathematical singularity
        clamped_risk = max(0.01, min(0.99, risk_30d))

        # Adjust shape parameter based on criticality degradation wear-out characteristics
        crit_upper = claimed_criticality.upper()
        if crit_upper == "CRITICAL":
            k = 2.5  # rapid accelerated wear
        elif crit_upper == "HIGH":
            k = 2.0
        elif crit_upper == "MEDIUM":
            k = 1.5
        else:
            k = 1.2

        scale_lambda = 30.0 / ((-math.log(1.0 - clamped_risk)) ** (1.0 / k))
        return scale_lambda, k

    @staticmethod
    def sample_failure_time(
        scale_lambda: float,
        shape_k: float,
        random_state: Optional[random.Random] = None,
    ) -> float:
        """
        Generates a stochastic failure time realization T (in days) using inverse CDF sampling.
        T = lambda * (-ln(u))^(1/k) where u ~ Uniform(0, 1)
        """
        rng = random_state or random
        u = rng.random()
        # Avoid log(0)
        u = max(1e-6, min(0.999999, u))
        failure_time_days = scale_lambda * ((-math.log(u)) ** (1.0 / shape_k))
        return failure_time_days

    @staticmethod
    def sample_from_empirical_curve(
        survival_curve: List[Dict[str, Any]],
        random_state: Optional[random.Random] = None,
    ) -> float:
        """
        Samples failure time directly from Layer 1 empirical discrete survival points.
        Returns the first day where (1 - survival_probability) >= u ~ Uniform(0, 1).
        """
        rng = random_state or random
        u = rng.random()
        for pt in survival_curve:
            d = pt.get("day") or pt.get("forecast_day", 1)
            sp = pt.get("survival_probability")
            if sp is not None and (1.0 - float(sp)) >= u:
                return float(d)
        return 999.0

    @staticmethod
    def get_survival_probability(t_days: float, scale_lambda: float, shape_k: float) -> float:
        """Returns survival probability S(t) at day t."""
        return math.exp(-((t_days / scale_lambda) ** shape_k))


class ScenarioRobustnessEngine:
    """
    Evaluates maintenance plan robustness against N=50 stochastic failure realizations.
    """

    def __init__(self, num_scenarios: int = 50, seed: int = 42):
        """
        Parameters:
        -----------
        num_scenarios : int
            Number of Monte Carlo failure-time scenarios to simulate (default = 50).
        seed : int
            Random seed for repeatable, deterministic simulations.
        """
        self.num_scenarios = num_scenarios
        self.seed = seed

    def evaluate_plan_robustness(
        self,
        tasks: List[MaintenanceTask],
        blocks: List[BlockWindow],
        schedule_result: OptimizationResult,
        planning_horizon_days: int = 7,
    ) -> ScenarioRobustnessResult:
        """
        Evaluates the scheduled plan across N=50 failure-time scenarios.

        Parameters:
        -----------
        tasks : List[MaintenanceTask]
            List of maintenance tasks.
        blocks : List[BlockWindow]
            Available block windows.
        schedule_result : OptimizationResult
            The optimization output to evaluate.
        planning_horizon_days : int
            Horizon duration (7 for weekly, 30 for monthly).

        Returns:
        --------
        ScenarioRobustnessResult
            Feasibility count, Robustness %, breakdown of prevented vs unplanned failures.
        """
        rng = random.Random(self.seed)

        # Build mapping of block_id -> day_index and task assignments
        block_day_map: Dict[str, int] = {}
        for b in blocks:
            # If day_index not set explicitly, map window_index proportionally across horizon
            d_idx = getattr(b, "day_index", 0)
            if d_idx == 0 and b.window_index > 0:
                d_idx = min(planning_horizon_days - 1, b.window_index)
            block_day_map[b.block_id] = d_idx

        # Task assignment day lookup
        task_scheduled_day: Dict[str, Optional[int]] = {}
        for item in schedule_result.scheduled_tasks:
            if item.status == "SCHEDULED" and item.assigned_block:
                task_scheduled_day[item.task_id] = block_day_map.get(item.assigned_block, 0)
            else:
                task_scheduled_day[item.task_id] = None

        # Precompute Weibull parameters for each task
        task_weibull: Dict[str, Tuple[float, float]] = {}
        for t in tasks:
            if t.weibull_lambda is not None and t.weibull_k is not None:
                task_weibull[t.task_id] = (t.weibull_lambda, t.weibull_k)
            else:
                task_weibull[t.task_id] = SurvivalCurveModel.derive_weibull_parameters(
                    risk_30d=t.risk_30d,
                    claimed_criticality=t.claimed_criticality,
                )

        evaluations: List[ScenarioEvaluation] = []
        feasible_count = 0
        total_simulated_failures = 0
        total_prevented_failures = 0
        vulnerable_asset_counts: Dict[str, int] = {}

        for scenario_idx in range(1, self.num_scenarios + 1):
            unplanned_failures: List[str] = []
            scenario_failures = 0
            scenario_prevented = 0
            scenario_feasible = True

            for t in tasks:
                if t.survival_curve and len(t.survival_curve) > 0:
                    failure_day = SurvivalCurveModel.sample_from_empirical_curve(
                        survival_curve=t.survival_curve,
                        random_state=rng,
                    )
                else:
                    scale_lambda, shape_k = task_weibull[t.task_id]
                    failure_day = SurvivalCurveModel.sample_failure_time(
                        scale_lambda=scale_lambda,
                        shape_k=shape_k,
                        random_state=rng,
                    )

                # Check if asset failure occurs within the planning horizon
                if failure_day <= planning_horizon_days:
                    scenario_failures += 1
                    scheduled_day = task_scheduled_day.get(t.task_id)

                    # Condition for successful prevention:
                    # Task is scheduled on or before the day the defect manifests into failure
                    if scheduled_day is not None and scheduled_day <= failure_day:
                        scenario_prevented += 1
                    else:
                        # Maintenance too late or task unassigned
                        unplanned_failures.append(
                            f"{t.task_id} ({t.segment}, failed day {failure_day:.1f}, "
                            f"sched day: {scheduled_day if scheduled_day is not None else 'UNASSIGNED'})"
                        )
                        vulnerable_asset_counts[t.segment] = (
                            vulnerable_asset_counts.get(t.segment, 0) + 1
                        )
                        # If a critical or high-risk task fails without maintenance, scenario fails
                        if t.is_high_risk_critical(0.65) or t.claimed_criticality.upper() == "CRITICAL":
                            scenario_feasible = False

            if scenario_feasible and len(unplanned_failures) == 0:
                feasible_count += 1
            elif scenario_feasible and len(unplanned_failures) <= 1:
                # Tolerable if non-critical
                feasible_count += 1
                scenario_feasible = True
            else:
                scenario_feasible = False

            total_simulated_failures += scenario_failures
            total_prevented_failures += scenario_prevented

            evaluations.append(
                ScenarioEvaluation(
                    scenario_index=scenario_idx,
                    is_feasible=scenario_feasible,
                    failures_simulated=scenario_failures,
                    failures_prevented_in_time=scenario_prevented,
                    unplanned_failures=unplanned_failures,
                    details=(
                        f"Scenario #{scenario_idx}: {scenario_prevented}/{scenario_failures} "
                        f"failures prevented. Status: {'FEASIBLE' if scenario_feasible else 'DISRUPTED'}"
                    ),
                )
            )

        robustness_pct = (feasible_count / self.num_scenarios) * 100.0
        prevention_rate = (
            (total_prevented_failures / total_simulated_failures * 100.0)
            if total_simulated_failures > 0
            else 100.0
        )

        top_vulnerable = sorted(
            vulnerable_asset_counts.keys(),
            key=lambda k: vulnerable_asset_counts[k],
            reverse=True,
        )[:5]

        summary = (
            f"Evaluated N={self.num_scenarios} Monte Carlo survival scenarios across {planning_horizon_days}-day horizon. "
            f"Robustness Score: {robustness_pct:.1f}% ({feasible_count}/{self.num_scenarios} feasible). "
            f"Failure Prevention Rate: {prevention_rate:.1f}% ({total_prevented_failures}/{total_simulated_failures} prevented in-time)."
        )

        return ScenarioRobustnessResult(
            total_scenarios=self.num_scenarios,
            feasible_scenarios_count=feasible_count,
            robustness_percentage=robustness_pct,
            total_simulated_failures=total_simulated_failures,
            failures_prevented_count=total_prevented_failures,
            failure_prevention_rate=prevention_rate,
            vulnerable_assets=top_vulnerable,
            scenario_evaluations=evaluations,
            summary=summary,
        )
