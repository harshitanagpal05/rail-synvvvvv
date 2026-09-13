"""RailSync 2.0 — Layer 0 generator.

Produces a realistic Indian Railways dataset with enough failure signal
to train Layer 1 (target: ~30% of segments fail over the observation window,
spread across asset types, ages, monsoon exposure, freight density).

Causal rules (kept from the original Layer 0 contract):
  - 2+ Grade-3 defects in last 90 days  -> ~8x base hazard
  - Track asset during monsoon (Jun-Sep) -> ~1.5x hazard
  - High freight density + age > 30y     -> ~2x hazard
  - Each active overdue task            -> ~1.5x hazard

Run:
    python scripts/layer0_generate.py --out Railsync_2.0_Layer_0_FINAL --seed 42
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

# Domain constants — mirrors Backend/railsync/layer0/corridors.py
CORRIDORS = {
    "delhi_mumbai": {
        "name": "Delhi-Mumbai Rajdhani Corridor",
        "divisions": ["Delhi", "Jaipur", "Kota", "Ratlam", "Vadodara", "Mumbai"],
        "total_km": 1384,
    },
    "delhi_howrah": {
        "name": "Delhi-Howrah Main Line",
        "divisions": ["Delhi", "Allahabad", "Mughal Sarai", "Dhanbad", "Howrah"],
        "total_km": 1447,
    },
    "chennai_mumbai": {
        "name": "Chennai-Mumbai Trunk Route",
        "divisions": ["Chennai", "Renigunta", "Guntakal", "Solapur", "Pune", "Mumbai"],
        "total_km": 1279,
    },
}

ASSET_TYPES = ["Track", "S&T", "Traction/OHE"]
DEPARTMENTS = ["Engineering", "Signalling", "Electrical"]
CURVE_GRADIENT_CLASSES = ["Low-Flat", "Low-Moderate", "Med-Moderate", "High-Steep"]
MONSOON_EXPOSURE_LEVELS = ["Low", "Medium", "High"]
FREIGHT_DENSITY_CLASSES = ["Low", "Medium", "High"]

OBSERVATION_START = date(2024, 1, 1)
OBSERVATION_END = date(2025, 12, 31)
MONTHS = 24

# Calibrated base daily hazard for a "median" segment.
# Chosen so that with the causal multipliers below, ~30% of segments fail
# within 24 months and the rest are right-censored.
BASE_DAILY_HAZARD = 0.00018


@dataclass
class Segment:
    id: str
    division: str
    corridor: str
    asset_type: str
    length_km: float
    age_years: float
    installation_year: int
    curve_gradient_class: str
    monsoon_exposure: str
    freight_density_class: str
    base_hazard: float  # adjusted for static covariates


@dataclass
class Defect:
    segment_id: str
    event_date: date
    grade: int  # 1, 2, 3


def generate_segments(rng: random.Random, segments_per_corridor: int = 25) -> list[Segment]:
    """Generate segments with realistic hazard-relevant attributes."""
    segments: list[Segment] = []
    seg_idx = 1
    for corridor_key, corridor in CORRIDORS.items():
        divisions = corridor["divisions"]
        total_km = corridor["total_km"]
        km_per_seg = total_km / segments_per_corridor
        for i in range(segments_per_corridor):
            div = divisions[i * len(divisions) // segments_per_corridor]
            age = rng.uniform(3, 50)
            asset_type = rng.choice(ASSET_TYPES)
            curve = rng.choice(CURVE_GRADIENT_CLASSES)
            monsoon = rng.choice(MONSOON_EXPOSURE_LEVELS)
            freight = rng.choice(FREIGHT_DENSITY_CLASSES)

            # Static hazard: older + high-freight + high-monsoon assets are riskier.
            age_factor = 1.0 + max(0.0, (age - 25) / 25.0) * 1.2
            monsoon_factor = {"Low": 1.0, "Medium": 1.3, "High": 1.6}[monsoon]
            freight_factor = {"Low": 1.0, "Medium": 1.2, "High": 1.5}[freight]
            curve_factor = {"Low-Flat": 1.0, "Low-Moderate": 1.05,
                            "Med-Moderate": 1.15, "High-Steep": 1.3}[curve]
            seg_hazard = (BASE_DAILY_HAZARD * age_factor * monsoon_factor
                          * freight_factor * curve_factor)

            segments.append(Segment(
                id=f"SEG-{seg_idx:03d}",
                division=div,
                corridor=corridor["name"],
                asset_type=asset_type,
                length_km=round(km_per_seg + rng.uniform(-3, 3), 2),
                age_years=round(age, 1),
                installation_year=2025 - int(age),
                curve_gradient_class=curve,
                monsoon_exposure=monsoon,
                freight_density_class=freight,
                base_hazard=seg_hazard,
            ))
            seg_idx += 1
    return segments


def _poisson(rng: random.Random, lam: float) -> int:
    """Poisson sampler (stdlib random.Random has no poisson in 3.10)."""
    import math
    if lam < 30:
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= rng.random()
            if p <= L:
                return k - 1
    else:
        # Normal approximation for large lam.
        return max(0, int(rng.gauss(lam, math.sqrt(lam)) + 0.5))


def generate_defects(
    rng: random.Random,
    segments: list[Segment],
) -> tuple[list[Defect], dict[str, list[Defect]]]:
    """Sample defects with frequency scaled to segment hazard."""
    all_defects: list[Defect] = []
    by_seg: dict[str, list[Defect]] = {s.id: [] for s in segments}
    for seg in segments:
        # Expected defects over 24 months ~ scaled by base hazard.
        expected = seg.base_hazard * 730 * 8  # scale so we see enough defects
        n_defects = _poisson(rng, expected)
        for _ in range(n_defects):
            event = OBSERVATION_START + timedelta(days=rng.randint(0, 729))
            grade = rng.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
            d = Defect(seg.id, event, grade)
            all_defects.append(d)
            by_seg[seg.id].append(d)
    return all_defects, by_seg


def simulate_failure(
    rng: random.Random,
    seg: Segment,
    defects: list[Defect],
) -> date | None:
    """Return first failure date if any, else None."""
    horizon_days = (OBSERVATION_END - OBSERVATION_START).days
    survival = 1.0
    failures: list[tuple[date, float]] = []
    for day_offset in range(horizon_days + 1):
        day = OBSERVATION_START + timedelta(days=day_offset)
        # Dynamic multipliers.
        recent_g3 = sum(
            1 for d in defects
            if d.grade == 3 and 0 <= (day - d.event_date).days <= 90
        )
        grade3_mult = 8.0 if recent_g3 >= 2 else (2.0 if recent_g3 == 1 else 1.0)

        monsoon_mult = 1.5 if (seg.asset_type == "Track"
                               and 6 <= day.month <= 9) else 1.0

        high_freight_old = (seg.freight_density_class == "High"
                            and seg.age_years > 30)
        freight_mult = 2.0 if high_freight_old else 1.0

        h_today = (seg.base_hazard * grade3_mult * monsoon_mult * freight_mult)
        h_today = min(h_today, 0.5)  # cap daily hazard
        if rng.random() < h_today:
            failures.append((day, h_today))
            return day
        survival *= (1.0 - h_today)
    return None


def build_maintenance_tasks(
    rng: random.Random,
    segments: list[Segment],
    failures: dict[str, date | None],
) -> list[dict]:
    """Generate a backlog of maintenance tasks. ~20% overrun pattern."""
    tasks: list[dict] = []
    task_idx = 1
    for seg in segments:
        # 2-4 tasks per segment over 24 months.
        n_tasks = rng.randint(2, 4)
        for _ in range(n_tasks):
            dept = rng.choice(DEPARTMENTS)
            planned_offset = rng.randint(0, 700)
            planned_date = OBSERVATION_START + timedelta(days=planned_offset)
            planned_dur = round(rng.uniform(2.0, 8.0), 2)
            # Overrun pattern: ~20% of tasks run long.
            if rng.random() < 0.20:
                actual_dur = round(planned_dur * rng.uniform(1.2, 1.6), 2)
                overrun_flag = 1
            else:
                actual_dur = round(planned_dur * rng.uniform(0.85, 1.05), 2)
                overrun_flag = 0
            # Overdue: tasks planned but not completed within 30 days.
            overdue = 1 if (overrun_flag and rng.random() < 0.5) else 0
            overdue_days = rng.randint(5, 60) if overdue else 0
            completion_date = (planned_date + timedelta(hours=actual_dur)
                               if not overdue else None)
            failure_date = failures.get(seg.id)
            if failure_date and planned_date > failure_date:
                # No point scheduling after the segment has failed.
                continue
            tasks.append({
                "task_id": f"TASK-{task_idx:05d}",
                "segment_id": seg.id,
                "division": seg.division,
                "department": dept,
                "type": rng.choice([
                    "Rail Grinding", "Tamping", "Weld Repair",
                    "Ballast Cleaning", "Sleeper Replacement",
                    "Signal Testing", "Axle Counter Calibration",
                    "Cable Replacement", "OHE Maintenance",
                    "Catenary Repair",
                ]),
                "planned_duration_hrs": planned_dur,
                "actual_duration_hrs": actual_dur,
                "planned_date": planned_date.isoformat(),
                "completion_date": completion_date.isoformat() if completion_date else "",
                "overdue_flag": overdue,
                "overdue_days": overdue_days,
                "overrun_flag": overrun_flag,
            })
            task_idx += 1
    return tasks


def build_timetable(rng: random.Random, days: int = 7) -> list[dict]:
    """Generate a deterministic IR-style weekly timetable for the demo corridor."""
    timetable = []
    base = datetime(2026, 9, 15, 0, 0, 0)
    # Fixed passenger trains: morning/evening slots per day (Rajdhani-shaped).
    passenger_slots = [(6, 10), (10, 30), (13, 30), (18, 15), (22, 0)]
    freight_slots = [(2, 0), (14, 45), (23, 30)]
    train_idx = 1
    for d in range(days):
        day = base + timedelta(days=d)
        for hour, minute in passenger_slots:
            start = day.replace(hour=hour, minute=minute)
            timetable.append({
                "train_id": f"PX-{train_idx:04d}",
                "start": start.isoformat(),
                "end": (start + timedelta(minutes=45)).isoformat(),
                "type": "passenger",
                "priority": "fixed",
            })
            train_idx += 1
        # Variable freight slots — 1 to 3 per day.
        n_freight = rng.randint(1, 3)
        chosen = rng.sample(freight_slots, k=min(n_freight, len(freight_slots)))
        for hour, minute in chosen:
            start = day.replace(hour=hour, minute=minute)
            timetable.append({
                "train_id": f"FX-{train_idx:04d}",
                "start": start.isoformat(),
                "end": (start + timedelta(minutes=30)).isoformat(),
                "type": "freight",
                "priority": "soft",
            })
            train_idx += 1
    return timetable


def build_corridor_blocks(timetable: list[dict]) -> list[dict]:
    """Derive candidate maintenance windows from timetable gaps.

    Block windows are gaps of >=120 minutes between consecutive train passages.
    """
    # Group by day.
    by_day: dict[str, list[dict]] = {}
    for t in timetable:
        day = t["start"][:10]
        by_day.setdefault(day, []).append(t)
    blocks: list[dict] = []
    block_idx = 1
    for day, trains in by_day.items():
        trains.sort(key=lambda x: x["start"])
        day_start = datetime.fromisoformat(day + "T00:00:00")
        day_end = day_start + timedelta(days=1)
        prev_end = day_start
        for t in trains:
            gap_start = prev_end
            gap_end = datetime.fromisoformat(t["start"])
            gap_min = (gap_end - gap_start).total_seconds() / 60
            if gap_min >= 120:
                blocks.append({
                    "block_id": f"BLK-{block_idx:04d}",
                    "date": day,
                    "start": gap_start.isoformat(),
                    "end": gap_end.isoformat(),
                    "duration_min": int(gap_min),
                    "type": "candidate",
                })
                block_idx += 1
            prev_end = max(prev_end, datetime.fromisoformat(t["end"]))
        # Final gap of the day.
        gap_min = (day_end - prev_end).total_seconds() / 60
        if gap_min >= 120:
            blocks.append({
                "block_id": f"BLK-{block_idx:04d}",
                "date": day,
                "start": prev_end.isoformat(),
                "end": day_end.isoformat(),
                "duration_min": int(gap_min),
                "type": "candidate",
            })
            block_idx += 1
    return blocks


def build_segment_monthly_panel(
    segments: list[Segment],
    defects_by_seg: dict[str, list[Defect]],
    failures: dict[str, date | None],
) -> list[dict]:
    """24 rows per segment with the ML features Layer 1 expects."""
    rows: list[dict] = []
    for seg in segments:
        seg_defects = defects_by_seg[seg.id]
        seg_fail = failures.get(seg.id)
        for m in range(MONTHS):
            month_date = (OBSERVATION_START.replace(day=1)
                          + timedelta(days=30 * m))
            month_start = month_date
            month_end = (month_start + timedelta(days=30))
            # Grade-3 defects in previous 90 days.
            g3_prev_90d = sum(
                1 for d in seg_defects
                if d.grade == 3
                and (month_start - d.event_date).days <= 90
                and d.event_date < month_start
            )
            defect_count_month = sum(
                1 for d in seg_defects
                if month_start <= d.event_date < month_end
            )
            failure_event = 1 if (seg_fail and month_start <= seg_fail < month_end) else 0
            monsoon_month = 1 if 6 <= month_start.month <= 9 else 0
            rows.append({
                "segment_id": seg.id,
                "month": month_start.strftime("%Y-%m-%d"),
                "division": seg.division,
                "asset_type": seg.asset_type,
                "age_years": seg.age_years,
                "freight_density_class": seg.freight_density_class,
                "monsoon_exposure": seg.monsoon_exposure,
                "grade3_defects_previous_90d": g3_prev_90d,
                "defect_count_month": defect_count_month,
                "failure_event": failure_event,
                "right_censored": 0 if (seg_fail and month_start > seg_fail) else 1,
                "monsoon_month": monsoon_month,
            })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="Generate Layer 0 synthetic dataset.")
    p.add_argument("--out", default="Railsync_2.0_Layer_0_FINAL",
                   help="Output directory for CSVs.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--segments-per-corridor", type=int, default=25)
    args = p.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out)

    print(f"Generating segments (seed={args.seed})...")
    segments = generate_segments(rng, args.segments_per_corridor)
    print(f"  {len(segments)} segments")

    print("Generating defects with hazard scaling...")
    all_defects, defects_by_seg = generate_defects(rng, segments)
    print(f"  {len(all_defects)} defect events")

    print("Simulating failures (causal hazard model)...")
    failures: dict[str, date | None] = {}
    failed_count = 0
    for seg in segments:
        fdate = simulate_failure(rng, seg, defects_by_seg[seg.id])
        failures[seg.id] = fdate
        if fdate is not None:
            failed_count += 1
    fail_rate = failed_count / len(segments) * 100
    print(f"  {failed_count}/{len(segments)} segments failed ({fail_rate:.1f}%)")

    print("Generating maintenance task backlog...")
    tasks = build_maintenance_tasks(rng, segments, failures)
    print(f"  {len(tasks)} tasks")

    print("Generating timetable + corridor blocks...")
    timetable = build_timetable(rng)
    blocks = build_corridor_blocks(timetable)
    print(f"  {len(timetable)} train records, {len(blocks)} block windows")

    print("Building segment-monthly panel...")
    panel = build_segment_monthly_panel(segments, defects_by_seg, failures)
    print(f"  {len(panel)} panel rows")

    print("Building survival outcomes...")
    outcomes = []
    for seg in segments:
        fdate = failures[seg.id]
        if fdate is not None:
            duration = (fdate - OBSERVATION_START).days
            outcomes.append({
                "segment_id": seg.id,
                "observation_start": OBSERVATION_START.isoformat(),
                "observation_end": OBSERVATION_END.isoformat(),
                "observed_end": fdate.isoformat(),
                "duration_days": duration,
                "failure_event": 1,
                "right_censored": 0,
            })
        else:
            outcomes.append({
                "segment_id": seg.id,
                "observation_start": OBSERVATION_START.isoformat(),
                "observation_end": OBSERVATION_END.isoformat(),
                "observed_end": OBSERVATION_END.isoformat(),
                "duration_days": (OBSERVATION_END - OBSERVATION_START).days,
                "failure_event": 0,
                "right_censored": 1,
            })

    print("Writing CSVs...")
    write_csv(out / "segments_master.csv",
              [{"id": s.id, "division": s.division,
                "asset_type": s.asset_type, "length_km": s.length_km,
                "age_years": s.age_years, "installation_year": s.installation_year,
                "curve_gradient_class": s.curve_gradient_class,
                "monsoon_exposure": s.monsoon_exposure,
                "freight_density_class": s.freight_density_class,
                "corridor": s.corridor}
               for s in segments])
    write_csv(out / "defect_events.csv",
              [{"segment_id": d.segment_id,
                "event_date": d.event_date.isoformat(),
                "grade": d.grade,
                "days_to_repair": random.Random(d.segment_id + d.event_date.isoformat()).randint(1, 14)}
               for d in all_defects])
    write_csv(out / "maintenance_tasks.csv", tasks)
    write_csv(out / "train_timetable.csv", timetable)
    write_csv(out / "corridor_blocks.csv", blocks)
    write_csv(out / "segment_monthly_panel.csv", panel)
    write_csv(out / "survival_outcomes.csv", outcomes)
    print(f"  -> {out}/")
    print("Done.")


if __name__ == "__main__":
    main()
