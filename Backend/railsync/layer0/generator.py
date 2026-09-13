"""RailSync 2.0 — Layer 0: Causal synthetic data generator for Indian Railways.

Generates segments, timetable slots, goods forecasts, and maintenance tasks
with deterministic seeding for reproducible demos.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from railsync.layer0.corridors import (
    ASSET_TYPES,
    CORRIDORS,
    CURVE_GRADIENT_CLASSES,
    DEPARTMENTS,
    FREIGHT_DENSITY_CLASSES,
    MONSOON_EXPOSURE_LEVELS,
    TASK_TYPES_BY_DEPT,
)


def generate_segments(seed: int = 42, segments_per_corridor: int = 10) -> list[dict[str, Any]]:
    """Generate realistic corridor segment records."""
    rng = random.Random(seed)
    segments = []
    seg_idx = 1

    for corridor_key, corridor in CORRIDORS.items():
        divisions = corridor["divisions"]
        total_km = corridor["total_km"]
        km_per_seg = total_km / segments_per_corridor

        for i in range(segments_per_corridor):
            div = divisions[i * len(divisions) // segments_per_corridor]
            age = rng.uniform(3, 45)
            install_year = 2026 - int(age)

            segments.append({
                "segment_id": f"SEG-{seg_idx:03d}",
                "division": div,
                "section": f"{div}-Sec{i + 1}",
                "corridor": corridor["name"],
                "asset_type": rng.choice(ASSET_TYPES),
                "length_km": round(km_per_seg + rng.uniform(-5, 5), 1),
                "age_years": round(age, 1),
                "installation_year": install_year,
                "curve_gradient_class": rng.choice(CURVE_GRADIENT_CLASSES),
                "monsoon_exposure": rng.choice(MONSOON_EXPOSURE_LEVELS),
                "freight_density_class": rng.choice(FREIGHT_DENSITY_CLASSES),
            })
            seg_idx += 1

    return segments


def generate_timetable(
    seed: int = 42,
    base_date: datetime | None = None,
    days: int = 7,
    trains_per_day: int = 18,
) -> list[dict[str, Any]]:
    """Generate timetable block-unavailability windows (train passages)."""
    rng = random.Random(seed)
    if base_date is None:
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    slots = []
    for day_offset in range(days):
        day = base_date + timedelta(days=day_offset)
        for t in range(trains_per_day):
            hour = rng.randint(4, 23)
            minute = rng.choice([0, 10, 20, 30, 40, 50])
            start = day.replace(hour=hour, minute=minute, second=0)
            duration_min = rng.choice([15, 20, 25, 30, 45])
            slots.append({
                "train_id": f"TR-{day_offset * 100 + t + 1:04d}",
                "start": start,
                "end": start + timedelta(minutes=duration_min),
                "priority": rng.choice(["rajdhani", "express", "mail", "passenger", "goods"]),
            })
    return slots


def generate_goods_forecast(
    seed: int = 42,
    base_date: datetime | None = None,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Generate goods train frequency forecast per day."""
    rng = random.Random(seed + 100)
    if base_date is None:
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    forecasts = []
    for day_offset in range(days):
        day = base_date + timedelta(days=day_offset)
        forecasts.append({
            "date": day.date().isoformat(),
            "expected_goods_trains": rng.randint(8, 28),
            "peak_hours": [rng.randint(0, 5), rng.randint(22, 23)],
            "congestion_level": rng.choice(["low", "medium", "high"]),
        })
    return forecasts


def generate_maintenance_tasks(
    segments: list[dict[str, Any]],
    seed: int = 42,
    tasks_per_segment: int = 2,
    base_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Generate maintenance task backlog for given segments."""
    rng = random.Random(seed + 200)
    if base_date is None:
        base_date = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)

    tasks = []
    task_idx = 1

    for seg in segments:
        n = rng.randint(1, tasks_per_segment + 1)
        for _ in range(n):
            dept = rng.choice(DEPARTMENTS)
            task_type = rng.choice(TASK_TYPES_BY_DEPT[dept])

            # Causal: older assets → higher base criticality
            age_factor = min(seg["age_years"] / 40.0, 1.0)
            base_crit = 1 + int(age_factor * 3)
            # Departments sometimes inflate claims
            inflation = rng.randint(0, 2)
            claimed = min(base_crit + inflation, 5)

            min_dur = round(rng.uniform(0.5, 4.0), 1)
            window_start = base_date + timedelta(hours=rng.randint(0, 48))
            window_end = window_start + timedelta(hours=rng.randint(4, 12))

            tasks.append({
                "task_id": f"TASK-{task_idx:03d}",
                "segment_id": seg["segment_id"],
                "department": dept,
                "task_type": task_type,
                "claimed_criticality": claimed,
                "min_duration_hrs": min_dur,
                "preferred_window_start": window_start,
                "preferred_window_end": window_end,
                "overdue": rng.random() < (0.15 + age_factor * 0.25),
                "status": "pending",
            })
            task_idx += 1

    return tasks


def generate_full_dataset(seed: int = 42) -> dict[str, Any]:
    """Generate a complete interconnected dataset for demo/seeding."""
    segments = generate_segments(seed=seed)
    tasks = generate_maintenance_tasks(segments, seed=seed)
    timetable = generate_timetable(seed=seed)
    goods = generate_goods_forecast(seed=seed)

    return {
        "segments": segments,
        "tasks": tasks,
        "timetable": timetable,
        "goods_forecast": goods,
    }
