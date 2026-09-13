"""
config.py - RailSync Layer 3 Optimization Engine Configuration
=============================================================
This file contains all configurable weights, thresholds, and solver parameters.
NOTE: The exact mathematical weights for RailSync objectives are configurable here
so your team can fine-tune them during simulation and field testing without changing
the core optimization solver code.

NOTE ON CP-SAT:
Google OR-Tools CP-SAT works with integer linear programming.
All floating-point weights and durations are scaled by an integer multiplier
(SCALE_FACTOR) internally to preserve decimal precision (e.g., 2.5 hrs -> 250 units).
"""

from dataclasses import dataclass
from typing import Optional, Dict, Tuple


@dataclass
class OptimizerConfig:
    # --------------------------------------------------------------------------
    # 1. SCALING FACTOR (For CP-SAT integer arithmetic)
    # --------------------------------------------------------------------------
    # Multiplier to convert floating point hours/risks to integers in CP-SAT
    # e.g., 2.5 hours * 100 = 250 integer units
    SCALE_FACTOR: int = 100

    # --------------------------------------------------------------------------
    # 2. RISK & CRITICALITY THRESHOLDS & POLICIES
    # --------------------------------------------------------------------------
    # High risk probability threshold (0.0 to 1.0)
    HIGH_RISK_THRESHOLD: float = 0.70

    # Criticality categories considered critical
    CRITICAL_CATEGORIES: Tuple[str, ...] = ("CRITICAL", "HIGH")

    # Criticality category priority scores (multipliers for urgency)
    CRITICALITY_PRIORITY_MAP: Optional[Dict[str, int]] = None

    # When True, high-risk critical tasks MUST be assigned to their next
    # feasible window (earliest chronological window without passenger conflict)
    # as a HARD constraint, rather than only a soft penalty.
    ENFORCE_STRICT_HIGH_RISK_NEXT_WINDOW: bool = True

    # --------------------------------------------------------------------------
    # 3. OBJECTIVE FUNCTION WEIGHTS (Configurable penalty/reward weights)
    # --------------------------------------------------------------------------
    # Penalty for leaving a maintenance task unassigned (should be highest)
    WEIGHT_UNASSIGNED_TASK_BASE_PENALTY: int = 10_000

    # Additional penalty for leaving high-risk (risk_30d > 0.7) critical tasks unassigned
    WEIGHT_UNASSIGNED_HIGH_RISK_PENALTY: int = 50_000

    # Weight for task urgency/delay (penalizes scheduling tasks in later windows)
    # Higher value = pushes all urgent tasks towards earlier available windows
    WEIGHT_WINDOW_DELAY_PENALTY: int = 500

    # Soft penalty weight per freight train delayed/impacted during block window
    WEIGHT_FREIGHT_CONFLICT_PENALTY: int = 250

    # Penalty for activating an additional maintenance block
    # Encourages consolidating/bundling multiple tasks into fewer total blocks
    WEIGHT_BLOCK_ACTIVATION_PENALTY: int = 1_000

    # Penalty per hour of unused maintenance block capacity
    # (Difference between block window duration and actual task duration)
    # Encourages tighter fitting of maintenance jobs to preserve track capacity
    WEIGHT_UNUSED_BLOCK_CAPACITY_PENALTY: int = 100

    # Backwards-compatible alias
    WEIGHT_UNUSED_DOWNTIME_PENALTY: int = 100

    # Bonus reward for scheduling a task in its department-preferred block window
    WEIGHT_PREFERRED_WINDOW_BONUS: int = 300

    # --------------------------------------------------------------------------
    # 4. SOLVER BEHAVIOR & TIMEOUT SETTINGS
    # --------------------------------------------------------------------------
    # Maximum time in seconds the solver is allowed to run
    SOLVER_TIMEOUT_SECONDS: float = 10.0

    # Fast re-optimization timeout (guaranteed < 5.0 seconds)
    FAST_REOPTIMIZE_TIMEOUT_SECONDS: float = 3.0

    # Number of parallel search workers (0 = use all available CPU cores)
    SOLVER_WORKERS: int = 4

    # Print CP-SAT solver search progress logs to console
    LOG_SOLVER_PROGRESS: bool = False

    def __post_init__(self):
        if self.CRITICALITY_PRIORITY_MAP is None:
            self.CRITICALITY_PRIORITY_MAP = {
                "CRITICAL": 10,
                "HIGH": 7,
                "MEDIUM": 4,
                "LOW": 1,
            }

    @classmethod
    def safety_first(cls) -> "OptimizerConfig":
        """
        Policy Preset: Safety-First
        ---------------------------
        - Prioritizes immediate execution of safety-critical work above all else.
        - Heavy penalties for task delay and unassigned tasks.
        - Strict enforcement of next feasible window for high-risk critical tasks.
        - Lower freight penalty weight so critical work is not deferred due to freight conflicts.
        """
        return cls(
            HIGH_RISK_THRESHOLD=0.65,
            ENFORCE_STRICT_HIGH_RISK_NEXT_WINDOW=True,
            WEIGHT_UNASSIGNED_TASK_BASE_PENALTY=30_000,
            WEIGHT_UNASSIGNED_HIGH_RISK_PENALTY=100_000,
            WEIGHT_WINDOW_DELAY_PENALTY=1_500,
            WEIGHT_FREIGHT_CONFLICT_PENALTY=100,
            WEIGHT_BLOCK_ACTIVATION_PENALTY=500,
            WEIGHT_UNUSED_BLOCK_CAPACITY_PENALTY=50,
            WEIGHT_PREFERRED_WINDOW_BONUS=200,
        )

    @classmethod
    def balanced(cls) -> "OptimizerConfig":
        """
        Policy Preset: Balanced (Default)
        ---------------------------------
        - Balances asset safety risk, freight throughput, and capacity utilization.
        """
        return cls()

    @classmethod
    def throughput_first(cls) -> "OptimizerConfig":
        """
        Policy Preset: Throughput-First
        -------------------------------
        - Prioritizes rail freight and network throughput.
        - High penalty for freight train delays.
        - Higher block activation penalty to strictly bundle maintenance into fewer windows.
        - Maintains strict passenger train protection (HARD constraint) and extreme-risk safety.
        """
        return cls(
            HIGH_RISK_THRESHOLD=0.75,
            ENFORCE_STRICT_HIGH_RISK_NEXT_WINDOW=True,
            WEIGHT_UNASSIGNED_TASK_BASE_PENALTY=8_000,
            WEIGHT_UNASSIGNED_HIGH_RISK_PENALTY=40_000,
            WEIGHT_WINDOW_DELAY_PENALTY=300,
            WEIGHT_FREIGHT_CONFLICT_PENALTY=800,
            WEIGHT_BLOCK_ACTIVATION_PENALTY=2_500,
            WEIGHT_UNUSED_BLOCK_CAPACITY_PENALTY=200,
            WEIGHT_PREFERRED_WINDOW_BONUS=400,
        )


# Default global configuration instance
DEFAULT_CONFIG = OptimizerConfig()

