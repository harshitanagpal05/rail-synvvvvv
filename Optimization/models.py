"""
models.py - RailSync Layer 3 Data Models
=======================================
Defines clean, typed data structures for maintenance tasks, block windows,
train conflicts, and optimization results.

These models allow another backend teammate to easily construct inputs
from JSON, database queries, or upstream microservices and parse the output.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class MaintenanceTask:
    """
    Represents an individual track/signal/traction maintenance job.

    Fields:
    -------
    task_id : str
        Unique identifier for the maintenance task (e.g. 'TASK-101').
    segment : str
        Track segment identifier (e.g. 'NDLS-GZB-UP').
    claimed_criticality : str
        Criticality level: 'CRITICAL', 'HIGH', 'MEDIUM', or 'LOW'.
    min_duration_hrs : float
        Minimum required continuous maintenance window in hours (e.g. 3.0).
    risk_30d : float
        30-day failure probability score between 0.0 (low) and 1.0 (imminent).
    preferred_window : Optional[str]
        Preferred block ID (if any) requested by the engineering team.
    description : Optional[str]
        Short human-readable description of the maintenance activity.
    """
    task_id: str
    segment: str
    claimed_criticality: str
    min_duration_hrs: float
    risk_30d: float
    preferred_window: Optional[str] = None
    description: Optional[str] = ""
    day_index: int = 0  # 0 to 6 for Weekly, 0 to 29 for Monthly
    horizon: str = "WEEKLY"  # 'WEEKLY' or 'MONTHLY'
    weibull_lambda: Optional[float] = None  # Scale parameter for Layer 1 survival curve
    weibull_k: Optional[float] = None  # Shape parameter for Layer 1 survival curve
    expected_downtime_days: Optional[float] = None  # ML expected asset downtime in days
    overrun_probability: Optional[float] = None  # ML predicted maintenance overrun probability [0, 1]
    confidence: Optional[str] = None  # ML prediction confidence ('high', 'medium', 'low')
    cold_start_fallback: Optional[bool] = None  # True if cold start prior was used
    survival_curve: Optional[List[Dict[str, Any]]] = None  # Empirical Layer 1 daily survival points

    def is_high_risk_critical(self, high_risk_threshold: float = 0.70) -> bool:
        """Helper to determine if task is a critical-safety job requiring immediate scheduling."""
        is_crit = self.claimed_criticality.upper() in ("CRITICAL", "HIGH")
        is_high_risk = self.risk_30d > high_risk_threshold
        return is_crit and is_high_risk


@dataclass
class BlockWindow:
    """
    Represents an available railway track possession / maintenance block window.

    Fields:
    -------
    block_id : str
        Unique identifier for the block (e.g. 'BLK-01').
    start_time : str
        Timestamp or human-readable start (e.g. '2026-09-11 01:00').
    end_time : str
        Timestamp or human-readable end (e.g. '2026-09-11 05:00').
    duration_hrs : float
        Continuous available block duration in hours (e.g. 4.0).
    window_index : int
        Chronological sequence index (0 = earliest/next window, 1 = subsequent, etc.).
    passenger_conflicts : Dict[str, int]
        Mapping of segment -> count of passenger trains conflicting during this block.
        If passenger_conflicts[segment] > 0, assigning a task on this segment is a HARD violation.
    freight_conflicts : Dict[str, int]
        Mapping of segment -> count of freight trains conflicting during this block.
        Freight conflicts are allowed but incur SOFT objective penalties.
    allowed_segments : Optional[List[str]]
        List of segments this block covers. If empty/None, block is open to all segments.
    """
    block_id: str
    start_time: str
    end_time: str
    duration_hrs: float
    window_index: int = 0
    passenger_conflicts: Dict[str, int] = field(default_factory=dict)
    freight_conflicts: Dict[str, int] = field(default_factory=dict)
    allowed_segments: Optional[List[str]] = None
    day_index: int = 0  # 0 to 6 for Weekly, 0 to 29 for Monthly
    horizon: str = "WEEKLY"  # 'WEEKLY' or 'MONTHLY'

    def has_passenger_conflict(self, segment: str) -> bool:
        """Returns True if assigning this block on `segment` causes a passenger train conflict (HARD)."""
        return self.passenger_conflicts.get(segment, 0) > 0

    def get_freight_conflict_count(self, segment: str) -> int:
        """Returns the number of freight trains delayed/impacted on `segment` during this block."""
        return self.freight_conflicts.get(segment, 0)


@dataclass
class ScheduledTaskResult:
    """Represents the scheduling decision for a specific maintenance task."""
    task_id: str
    assigned_block: Optional[str]
    segment: str
    duration_hrs: float
    claimed_criticality: str
    risk_30d: float
    is_high_risk_critical: bool
    window_index: Optional[int] = None
    freight_conflict_count: int = 0
    freight_penalty_score: float = 0.0
    status: str = "SCHEDULED"  # 'SCHEDULED' or 'UNASSIGNED'
    remarks: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BlockSummaryResult:
    """Summary of utilization and train impact for a specific maintenance block window."""
    block_id: str
    window_index: int
    duration_hrs: float
    is_utilized: bool
    assigned_tasks: List[str] = field(default_factory=list)
    segments_blocked: List[str] = field(default_factory=list)
    total_freight_delays: int = 0
    utilized_hours_max: float = 0.0
    unused_capacity_hrs: float = 0.0
    unused_hours: float = 0.0  # Backwards-compatible alias

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationResult:
    """
    Comprehensive output of the RailSync Layer 3 Optimization Engine.

    Fields:
    -------
    solver_status : str
        'OPTIMAL', 'FEASIBLE', 'INFEASIBLE', or 'MODEL_INVALID'
    total_tasks : int
        Total tasks submitted
    scheduled_tasks_count : int
        Number of tasks successfully assigned to a window
    unassigned_tasks_count : int
        Number of tasks that could not be assigned
    active_blocks_count : int
        Number of distinct block windows utilized
    total_freight_trains_delayed : int
        Total freight train conflicts across all scheduled assignments
    solver_run_time_seconds : float
        Elapsed time taken by CP-SAT solver in seconds
    objective_value : float
        Final objective score calculated by CP-SAT
    scheduled_tasks : List[ScheduledTaskResult]
        Detailed assignment per task
    block_summaries : List[BlockSummaryResult]
        Utilization and impact summary for each block window
    """
    solver_status: str
    total_tasks: int
    scheduled_tasks_count: int
    unassigned_tasks_count: int
    active_blocks_count: int
    total_freight_trains_delayed: int
    solver_run_time_seconds: float
    objective_value: float
    scheduled_tasks: List[ScheduledTaskResult] = field(default_factory=list)
    block_summaries: List[BlockSummaryResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        scheduled_items = [t.to_dict() for t in self.scheduled_tasks if t.status == "SCHEDULED"]
        unassigned_items = [t.to_dict() for t in self.scheduled_tasks if t.status == "UNASSIGNED"]
        all_task_dicts = [t.to_dict() for t in self.scheduled_tasks]

        return {
            "solver_status": self.solver_status,
            "objective_score": self.objective_value,
            "objective_value": self.objective_value,
            "runtime": self.solver_run_time_seconds,
            "solver_run_time_seconds": self.solver_run_time_seconds,
            "total_tasks": self.total_tasks,
            "scheduled_tasks_count": self.scheduled_tasks_count,
            "unassigned_tasks_count": self.unassigned_tasks_count,
            "active_blocks": self.active_blocks_count,
            "active_blocks_count": self.active_blocks_count,
            "freight_conflicts": self.total_freight_trains_delayed,
            "total_freight_trains_delayed": self.total_freight_trains_delayed,
            "scheduled_tasks": scheduled_items,
            "unassigned_tasks": unassigned_items,
            "all_tasks": all_task_dicts,
            "block_summaries": [b.to_dict() for b in self.block_summaries],
        }


# ==============================================================================
# What-If Disruption Scenario Models
# ==============================================================================

@dataclass
class DisruptionScenario:
    """
    Represents an operational disruption or dynamic change injected into the schedule.

    Fields:
    -------
    scenario_id : str
        Short identifier for the disruption scenario (e.g. 'SCN-DEFECT-01').
    description : str
        Human-readable description of the disruption.
    emergency_tasks : List[MaintenanceTask]
        Newly detected emergency tasks (e.g. rail fracture, OHE breakdown).
    cancelled_blocks : List[str]
        Block window IDs that are revoked/cancelled due to traffic.
    modified_passenger_conflicts : Dict[str, Dict[str, int]]
        Mapping of block_id -> {segment: count} to add/update passenger conflicts.
    modified_block_durations : Dict[str, float]
        Mapping of block_id -> new_duration_hrs (e.g. window truncated).
    locked_assignments : Dict[str, str]
        Mapping of task_id -> block_id for tasks already underway that cannot move.
    """
    scenario_id: str
    description: str
    emergency_tasks: List[MaintenanceTask] = field(default_factory=list)
    cancelled_blocks: List[str] = field(default_factory=list)
    modified_passenger_conflicts: Dict[str, Dict[str, int]] = field(default_factory=dict)
    modified_block_durations: Dict[str, float] = field(default_factory=dict)
    locked_assignments: Dict[str, str] = field(default_factory=dict)


@dataclass
class TaskChangeDiff:
    """Detailed diff for a single task affected by disruption re-optimization."""
    task_id: str
    segment: str
    original_block: Optional[str]
    new_block: Optional[str]
    change_type: str  # 'UNCHANGED', 'RESCHEDULED', 'NEWLY_SCHEDULED', 'DISPLACED_UNASSIGNED'
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BlockChangeDiff:
    """Detailed diff for a block window affected by disruption re-optimization."""
    block_id: str
    original_task_count: int
    new_task_count: int
    tasks_added: List[str]
    tasks_removed: List[str]
    status_change: str  # 'UNCHANGED', 'ACTIVATED', 'DEACTIVATED', 'MODIFIED'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WhatIfResult:
    """
    Comprehensive output of a What-If Disruption Re-Optimization.
    """
    scenario_id: str
    description: str
    solver_status: str
    affected_tasks_count: int
    affected_tasks: List[TaskChangeDiff]
    changed_blocks: List[BlockChangeDiff]
    baseline_schedule: OptimizationResult
    revised_schedule: OptimizationResult
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "solver_status": self.solver_status,
            "affected_tasks_count": self.affected_tasks_count,
            "affected_tasks": [t.to_dict() for t in self.affected_tasks],
            "changed_blocks": [b.to_dict() for b in self.changed_blocks],
            "baseline_metrics": {
                "scheduled": self.baseline_schedule.scheduled_tasks_count,
                "unassigned": self.baseline_schedule.unassigned_tasks_count,
                "freight_delayed": self.baseline_schedule.total_freight_trains_delayed,
            },
            "revised_metrics": {
                "scheduled": self.revised_schedule.scheduled_tasks_count,
                "unassigned": self.revised_schedule.unassigned_tasks_count,
                "freight_delayed": self.revised_schedule.total_freight_trains_delayed,
            },
            "summary": self.summary,
        }


# ==============================================================================
# Multi-Horizon Planning Models (Weekly & Monthly)
# ==============================================================================

class HorizonType:
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


@dataclass
class MultiHorizonScheduleResult:
    """
    Combined multi-horizon schedule result holding weekly tactical and monthly strategic views.
    """
    horizon: str  # 'WEEKLY' (7-day) or 'MONTHLY' (30-day)
    schedule: OptimizationResult
    day_schedules: Dict[int, List[ScheduledTaskResult]] = field(default_factory=dict)
    horizon_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "horizon": self.horizon,
            "schedule": self.schedule.to_dict(),
            "day_schedules": {
                str(k): [t.to_dict() for t in v] for k, v in self.day_schedules.items()
            },
            "horizon_summary": self.horizon_summary,
        }


# ==============================================================================
# Policy Presets & Pareto Frontier Models
# ==============================================================================

class PolicyPreset:
    SAFETY_FIRST = "SAFETY_FIRST"
    BALANCED = "BALANCED"
    THROUGHPUT_FIRST = "THROUGHPUT_FIRST"


@dataclass
class ParetoPoint:
    """
    Represents a single evaluated point on the multi-objective Pareto frontier.
    """
    preset_name: str
    safety_score: float  # 0 to 100 (higher = safer, penalizes high-risk unassigned/delayed)
    freight_trains_delayed: int  # count of delayed freight trains
    active_blocks: int
    scheduled_tasks: int
    unassigned_tasks: int
    runtime_seconds: float
    objective_value: float
    schedule: OptimizationResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset_name": self.preset_name,
            "safety_score": round(self.safety_score, 2),
            "freight_trains_delayed": self.freight_trains_delayed,
            "active_blocks": self.active_blocks,
            "scheduled_tasks": self.scheduled_tasks,
            "unassigned_tasks": self.unassigned_tasks,
            "runtime_seconds": self.runtime_seconds,
            "objective_value": self.objective_value,
            "schedule": self.schedule.to_dict(),
        }


@dataclass
class ParetoFrontierResult:
    """
    Holds Pareto analysis across Safety-First, Balanced, and Throughput-First policies.
    """
    points: List[ParetoPoint] = field(default_factory=list)
    recommended_preset: str = PolicyPreset.BALANCED
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "points": [p.to_dict() for p in self.points],
            "recommended_preset": self.recommended_preset,
            "summary": self.summary,
        }


# ==============================================================================
# Layer 1 Survival Curves & Scenario Robustness Models (Monte Carlo N=50)
# ==============================================================================

@dataclass
class ScenarioEvaluation:
    """
    Evaluation of a maintenance plan under a single simulated failure-time realization.
    """
    scenario_index: int
    is_feasible: bool
    failures_simulated: int
    failures_prevented_in_time: int
    unplanned_failures: List[str] = field(default_factory=list)
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioRobustnessResult:
    """
    Robustness evaluation across N=50 Monte Carlo failure scenarios sampled from Layer 1 survival curves.
    """
    total_scenarios: int
    feasible_scenarios_count: int
    robustness_percentage: float  # (feasible_scenarios_count / total_scenarios) * 100
    total_simulated_failures: int
    failures_prevented_count: int
    failure_prevention_rate: float
    vulnerable_assets: List[str] = field(default_factory=list)
    scenario_evaluations: List[ScenarioEvaluation] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_scenarios": self.total_scenarios,
            "feasible_scenarios_count": self.feasible_scenarios_count,
            "robustness_percentage": round(self.robustness_percentage, 2),
            "total_simulated_failures": self.total_simulated_failures,
            "failures_prevented_count": self.failures_prevented_count,
            "failure_prevention_rate": round(self.failure_prevention_rate, 2),
            "vulnerable_assets": self.vulnerable_assets,
            "scenario_evaluations": [s.to_dict() for s in self.scenario_evaluations],
            "summary": self.summary,
        }


# ==============================================================================
# Plan B Contingency Models (Top-5 Precomputed Disruption Plans)
# ==============================================================================

@dataclass
class PlanBContingency:
    """
    A pre-computed, instant fallback plan (Plan B) for a specific high-impact disruption.
    """
    disruption_id: str
    scenario_title: str
    probability_weight: float
    severity: str  # 'HIGH', 'CRITICAL', 'MODERATE'
    disruption: DisruptionScenario
    revised_schedule: OptimizationResult
    diff_summary: str
    what_changed: List[TaskChangeDiff] = field(default_factory=list)
    reason_why: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "disruption_id": self.disruption_id,
            "scenario_title": self.scenario_title,
            "probability_weight": self.probability_weight,
            "severity": self.severity,
            "revised_schedule": self.revised_schedule.to_dict(),
            "diff_summary": self.diff_summary,
            "what_changed": [c.to_dict() for c in self.what_changed],
            "reason_why": self.reason_why,
        }


@dataclass
class PlanBRepository:
    """
    Precomputed repository storing fallback 'Plan B' schedules for top-5 operational disruptions.
    """
    baseline_schedule: OptimizationResult
    contingencies: List[PlanBContingency] = field(default_factory=list)
    generated_at: str = ""

    def get_plan(self, disruption_id: str) -> Optional[PlanBContingency]:
        """Lookup precomputed contingency plan by disruption ID for instant zero-wait response."""
        for c in self.contingencies:
            if c.disruption_id == disruption_id:
                return c
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "baseline_metrics": {
                "scheduled": self.baseline_schedule.scheduled_tasks_count,
                "unassigned": self.baseline_schedule.unassigned_tasks_count,
                "freight_delayed": self.baseline_schedule.total_freight_trains_delayed,
            },
            "top_contingencies_count": len(self.contingencies),
            "contingencies": [c.to_dict() for c in self.contingencies],
        }

