"""
multi_horizon.py - RailSync Layer 3 Multi-Horizon Planning Engine
================================================================
Generates and manages multi-horizon maintenance schedules:
1. Weekly Plan (7-Day Tactical Operational Schedule)
2. Monthly Plan (30-Day Master Strategic Maintenance Allocation)
"""

from typing import List, Dict, Optional, Any
from collections import defaultdict

try:
    from .models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ScheduledTaskResult,
        MultiHorizonScheduleResult,
        HorizonType,
    )
    from .config import OptimizerConfig, DEFAULT_CONFIG
    from .optimizer import RailSyncOptimizer
except (ImportError, ValueError):
    from models import (
        MaintenanceTask,
        BlockWindow,
        OptimizationResult,
        ScheduledTaskResult,
        MultiHorizonScheduleResult,
        HorizonType,
    )
    from config import OptimizerConfig, DEFAULT_CONFIG
    from optimizer import RailSyncOptimizer


class MultiHorizonPlanner:
    """
    Coordinates tactical 7-day weekly planning and 30-day strategic monthly planning.
    """

    def __init__(self, optimizer: Optional[RailSyncOptimizer] = None):
        self.optimizer = optimizer or RailSyncOptimizer()

    def generate_weekly_plan(
        self,
        tasks: List[MaintenanceTask],
        blocks: List[BlockWindow],
        config: Optional[OptimizerConfig] = None,
    ) -> MultiHorizonScheduleResult:
        """
        Generates a 7-day tactical operational maintenance schedule.

        Parameters:
        -----------
        tasks : List[MaintenanceTask]
            Tasks scheduled for the current week.
        blocks : List[BlockWindow]
            Block possession windows available over the next 7 days (day_index 0 to 6).
        config : Optional[OptimizerConfig]
            Custom configuration for weekly scheduling.

        Returns:
        --------
        MultiHorizonScheduleResult
            Weekly schedule partitioned by day.
        """
        active_optimizer = RailSyncOptimizer(config=config) if config else self.optimizer

        # Filter or validate tasks/blocks for weekly horizon (7 days)
        weekly_blocks = [
            b for b in blocks if getattr(b, "day_index", 0) < 7
        ] if any(getattr(b, "day_index", 0) > 0 for b in blocks) else blocks

        weekly_tasks = [
            t for t in tasks if getattr(t, "day_index", 0) < 7
        ] if any(getattr(t, "day_index", 0) > 0 for t in tasks) else tasks

        result = active_optimizer.optimize(tasks=weekly_tasks, blocks=weekly_blocks)

        # Build day-wise breakdown
        block_to_day: Dict[str, int] = {
            b.block_id: getattr(b, "day_index", b.window_index % 7) for b in weekly_blocks
        }

        day_schedules: Dict[int, List[ScheduledTaskResult]] = defaultdict(list)
        for st in result.scheduled_tasks:
            if st.status == "SCHEDULED" and st.assigned_block:
                assigned_day = block_to_day.get(st.assigned_block, 0)
                day_schedules[assigned_day].append(st)
            else:
                day_schedules[-1].append(st)  # -1 represents unassigned

        # Compute weekly summary metrics
        high_risk_scheduled = sum(
            1 for t in result.scheduled_tasks
            if t.status == "SCHEDULED" and t.is_high_risk_critical
        )
        total_high_risk = sum(1 for t in weekly_tasks if t.is_high_risk_critical(0.70))

        weekly_summary = {
            "horizon": HorizonType.WEEKLY,
            "horizon_days": 7,
            "total_tasks": len(weekly_tasks),
            "scheduled_tasks": result.scheduled_tasks_count,
            "unassigned_tasks": result.unassigned_tasks_count,
            "high_risk_completion_rate": (
                f"{high_risk_scheduled}/{total_high_risk} (100.0%)"
                if total_high_risk == 0
                else f"{high_risk_scheduled}/{total_high_risk} ({high_risk_scheduled / total_high_risk * 100:.1f}%)"
            ),
            "active_blocks_used": result.active_blocks_count,
            "freight_trains_delayed": result.total_freight_trains_delayed,
            "days_with_active_maintenance": len([d for d, tasks_list in day_schedules.items() if d >= 0 and len(tasks_list) > 0]),
        }

        return MultiHorizonScheduleResult(
            horizon=HorizonType.WEEKLY,
            schedule=result,
            day_schedules=dict(day_schedules),
            horizon_summary=weekly_summary,
        )

    def generate_monthly_plan(
        self,
        tasks: List[MaintenanceTask],
        blocks: List[BlockWindow],
        config: Optional[OptimizerConfig] = None,
    ) -> MultiHorizonScheduleResult:
        """
        Generates a 30-day strategic master maintenance schedule.

        Parameters:
        -----------
        tasks : List[MaintenanceTask]
            Tasks requiring execution across the 30-day window.
        blocks : List[BlockWindow]
            Block possession windows available over the next 30 days (day_index 0 to 29).
        config : Optional[OptimizerConfig]
            Custom configuration for monthly scheduling.

        Returns:
        --------
        MultiHorizonScheduleResult
            Monthly schedule partitioned across 4-5 weekly cycles and 30 days.
        """
        active_optimizer = RailSyncOptimizer(config=config) if config else self.optimizer

        result = active_optimizer.optimize(tasks=tasks, blocks=blocks)

        block_to_day: Dict[str, int] = {
            b.block_id: getattr(b, "day_index", (b.window_index * 2) % 30) for b in blocks
        }

        day_schedules: Dict[int, List[ScheduledTaskResult]] = defaultdict(list)
        week_schedules: Dict[int, int] = defaultdict(int)

        for st in result.scheduled_tasks:
            if st.status == "SCHEDULED" and st.assigned_block:
                assigned_day = block_to_day.get(st.assigned_block, 0)
                day_schedules[assigned_day].append(st)
                week_idx = assigned_day // 7 + 1
                week_schedules[week_idx] += 1
            else:
                day_schedules[-1].append(st)

        total_expected_downtime = sum(
            getattr(t, "expected_downtime_days", 0.0) or 0.0 for t in tasks
        )
        prevented_downtime = sum(
            getattr(t, "expected_downtime_days", 0.0) or 0.0
            for t in tasks
            if any(st.task_id == t.task_id and st.status == "SCHEDULED" for st in result.scheduled_tasks)
        )

        monthly_summary = {
            "horizon": HorizonType.MONTHLY,
            "horizon_days": 30,
            "total_tasks": len(tasks),
            "scheduled_tasks": result.scheduled_tasks_count,
            "unassigned_tasks": result.unassigned_tasks_count,
            "weekly_distribution": {f"Week {w}": count for w, count in sorted(week_schedules.items())},
            "active_blocks_used": result.active_blocks_count,
            "total_freight_delays": result.total_freight_trains_delayed,
            "total_expected_downtime_days": round(total_expected_downtime, 2),
            "prevented_downtime_days": round(prevented_downtime, 2),
            "network_asset_availability_ratio": (
                round(1.0 - (result.active_blocks_count / max(1, len(blocks))), 3)
            ),
        }

        return MultiHorizonScheduleResult(
            horizon=HorizonType.MONTHLY,
            schedule=result,
            day_schedules=dict(day_schedules),
            horizon_summary=monthly_summary,
        )
