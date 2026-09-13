"""
RailSync Optimization Engine (Layer 3)
======================================
AI-Powered Automatic Block Planning & Digital Twin for Indian Railways.

Provides CP-SAT constraint programming optimizer for scheduling track maintenance
blocks while respecting passenger safety (HARD), freight throughput (SOFT),
and high-risk asset failure prioritization.

Public Entry Points:
--------------------
- optimize_schedule(tasks, blocks, config=None) -> OptimizationResult
- what_if_reoptimize(tasks, blocks, disruption, config=None) -> WhatIfResult
- generate_weekly_plan(tasks, blocks, config=None) -> MultiHorizonScheduleResult
- generate_monthly_plan(tasks, blocks, config=None) -> MultiHorizonScheduleResult
- compute_pareto_frontier(tasks, blocks) -> ParetoFrontierResult
- evaluate_scenario_robustness(tasks, blocks, ...) -> ScenarioRobustnessResult
- generate_plan_b_contingencies(tasks, blocks, ...) -> PlanBRepository
- reoptimize_fast(tasks, blocks, disruption, ...) -> WhatIfResult
"""

from .models import (
    MaintenanceTask,
    BlockWindow,
    OptimizationResult,
    ScheduledTaskResult,
    BlockSummaryResult,
    DisruptionScenario,
    TaskChangeDiff,
    BlockChangeDiff,
    WhatIfResult,
    MultiHorizonScheduleResult,
    ParetoPoint,
    ParetoFrontierResult,
    ScenarioEvaluation,
    ScenarioRobustnessResult,
    PlanBContingency,
    PlanBRepository,
    PolicyPreset,
    HorizonType,
)
from .config import OptimizerConfig, DEFAULT_CONFIG
from .optimizer import (
    RailSyncOptimizer,
    optimize_schedule,
    what_if_reoptimize,
    generate_weekly_plan,
    generate_monthly_plan,
    compute_pareto_frontier,
    evaluate_scenario_robustness,
    generate_plan_b_contingencies,
    reoptimize_fast,
    print_schedule_table,
)
from .what_if import WhatIfEngine, print_what_if_table
from .robustness import SurvivalCurveModel, ScenarioRobustnessEngine
from .multi_horizon import MultiHorizonPlanner
from .pareto import ParetoFrontierAnalyzer
from .contingency import ContingencyEngine

__all__ = [
    # Main integration functions
    "optimize_schedule",
    "what_if_reoptimize",
    "generate_weekly_plan",
    "generate_monthly_plan",
    "compute_pareto_frontier",
    "evaluate_scenario_robustness",
    "generate_plan_b_contingencies",
    "reoptimize_fast",
    # Core Classes
    "RailSyncOptimizer",
    "WhatIfEngine",
    "SurvivalCurveModel",
    "ScenarioRobustnessEngine",
    "MultiHorizonPlanner",
    "ParetoFrontierAnalyzer",
    "ContingencyEngine",
    # Data Models
    "MaintenanceTask",
    "BlockWindow",
    "OptimizationResult",
    "ScheduledTaskResult",
    "BlockSummaryResult",
    "DisruptionScenario",
    "TaskChangeDiff",
    "BlockChangeDiff",
    "WhatIfResult",
    "MultiHorizonScheduleResult",
    "ParetoPoint",
    "ParetoFrontierResult",
    "ScenarioEvaluation",
    "ScenarioRobustnessResult",
    "PlanBContingency",
    "PlanBRepository",
    "PolicyPreset",
    "HorizonType",
    # Configuration
    "OptimizerConfig",
    "DEFAULT_CONFIG",
    # Utilities
    "print_schedule_table",
    "print_what_if_table",
]

