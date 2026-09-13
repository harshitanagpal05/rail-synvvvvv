"""RailSync 2.0 — Database seed script.

Populates Supabase with corridor segments and Layer 1 risk predictions.
Synthetic maintenance tasks are NOT inserted unless explicitly requested.

Run via:
    python -m app.seed --layer0 Railsync_2.0_Layer_0_FINAL
    python -m app.seed --with-tasks --layer0 Railsync_2.0_Layer_0_FINAL
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.core.logging import get_logger
from app.db import repositories as repo
from app.db.database import get_session_factory
from app.integrations import layer1
from app.services import optimization_service
from railsync.layer0.generator import generate_full_dataset

log = get_logger("seed")

_LAYER0_CANDIDATES = [
    Path("Railsync_2.0_Layer_0_FINAL"),
    Path("../Railsync_2.0_Layer_0_FINAL"),
]


def _resolve_layer0_dir(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    return next((d for d in _LAYER0_CANDIDATES if d.exists()), None)


def load_segments_from_layer0(data_dir: Path) -> list[dict]:
    seg = pd.read_csv(data_dir / "segments_master.csv")
    return [
        {
            "segment_id": str(row["id"]),
            "division": str(row["division"]),
            "section": f"{row['division']}-Sec",
            "corridor": str(row.get("corridor", row["division"])),
            "asset_type": str(row["asset_type"]),
            "length_km": float(row["length_km"]),
            "age_years": float(row["age_years"]),
            "installation_year": int(row.get("installation_year", 2026 - int(row["age_years"]))),
            "curve_gradient_class": str(row.get("curve_gradient_class", "Med-Moderate")),
            "monsoon_exposure": str(row.get("monsoon_exposure", "Low")),
            "freight_density_class": str(row.get("freight_density_class", "Medium")),
        }
        for _, row in seg.iterrows()
    ]


def load_tasks_from_layer0(data_dir: Path, limit: int | None = None) -> list[dict]:
    tasks = pd.read_csv(data_dir / "maintenance_tasks.csv")
    tasks["planned_date"] = pd.to_datetime(tasks["planned_date"], errors="coerce")
    tasks = tasks.sort_values("planned_date", ascending=False)
    if limit:
        tasks = tasks.head(limit)

    dept_map = {
        "Engineering": "TRACK",
        "Electrical": "OHE",
        "Signal": "SIG",
        "Telecom": "TELE",
    }
    rows = []
    for _, row in tasks.iterrows():
        dept = dept_map.get(str(row.get("department", "Engineering")), "TRACK")
        planned = row.get("planned_date")
        rows.append({
            "task_id": str(row["task_id"]),
            "segment_id": str(row["segment_id"]),
            "department": dept,
            "task_type": str(row.get("type", "Inspection")),
            "claimed_criticality": min(5, max(1, int(row.get("overdue_flag", 0)) + 2)),
            "min_duration_hrs": float(row.get("planned_duration_hrs", 2.0)),
            "preferred_window_start": planned,
            "preferred_window_end": planned + pd.Timedelta(hours=8) if pd.notna(planned) else None,
            "planned_duration_hrs": float(row.get("planned_duration_hrs", 2.0)),
            "actual_duration_hrs": float(row["actual_duration_hrs"]) if pd.notna(row.get("actual_duration_hrs")) else None,
            "overdue": bool(int(row.get("overdue_flag", 0))),
            "status": "pending",
        })
    return rows


def seed_database(
    seed: int = 42,
    run_initial_optimization: bool = True,
    layer0_dir: Path | None = None,
    with_tasks: bool = False,
    with_synthetic: bool = False,
    task_limit: int | None = None,
) -> None:
    """Populate database. Tasks require --with-tasks; never auto-seeded on boot."""
    session_factory = get_session_factory()
    session = session_factory()

    try:
        log.info("Starting RailSync database seed (tasks=%s, synthetic=%s)...", with_tasks, with_synthetic)

        if layer0_dir:
            segments_data = load_segments_from_layer0(layer0_dir)
            tasks_data = load_tasks_from_layer0(layer0_dir, limit=task_limit) if with_tasks else []
            log.info("Loaded Layer 0: %d segments, %d tasks", len(segments_data), len(tasks_data))
        elif with_synthetic:
            data = generate_full_dataset(seed=seed)
            segments_data = data["segments"]
            tasks_data = data["tasks"] if with_tasks else []
            log.info("Synthetic generator: %d segments, %d tasks", len(segments_data), len(tasks_data))
        else:
            log.error(
                "No data source. Pass --layer0 Railsync_2.0_Layer_0_FINAL "
                "or --synthetic (with optional --with-tasks)."
            )
            return

        inserted_segments = 0
        for s in segments_data:
            if not repo.get_segment(session, s["segment_id"]):
                repo.upsert_segment(session, **s)
                inserted_segments += 1
        log.info("Inserted %d new segments (%d total)", inserted_segments, len(segments_data))

        for s in segments_data:
            risk_pred = layer1.predict_risk(s)
            repo.save_risk_prediction(session, **{
                "segment_id": s["segment_id"],
                "risk_30d": risk_pred["risk_30d"],
                "expected_downtime_days": risk_pred["expected_downtime_days"],
                "preventive_block_duration_hrs": risk_pred["preventive_block_duration_hrs"],
                "confidence": risk_pred["confidence"],
                "survival_curve": risk_pred.get("survival_curve"),
                "feature_contributions": risk_pred.get("feature_contributions"),
                "model_version": risk_pred.get("model_version"),
            })
        log.info("Stored %d Layer 1 risk predictions", len(segments_data))

        inserted_tasks = 0
        if with_tasks:
            for t in tasks_data:
                if not repo.get_task(session, t["task_id"]):
                    repo.upsert_task(session, **t)
                    inserted_tasks += 1
            log.info("Inserted %d maintenance tasks", inserted_tasks)
        else:
            log.info("Skipped task seeding (use --with-tasks to load Layer 0 tasks)")

        session.commit()

        if run_initial_optimization and with_tasks and inserted_tasks > 0:
            log.info("Running baseline optimization on seeded tasks...")
            opt_resp = optimization_service.run_optimization(session, policy="balanced", horizon="weekly")
            log.info(
                "Plan created: feasible=%s, assignments=%d",
                opt_resp.feasible, len(opt_resp.assignments),
            )
        elif run_initial_optimization and not with_tasks:
            log.info("Skipped optimization — no tasks seeded. POST tasks via API first.")

        log.info("Database seeding completed.")

    except Exception as exc:
        session.rollback()
        log.error("Failed to seed database: %s", exc, exc_info=True)
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="RailSync 2.0 Database Seeder")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--layer0", type=str, default=None, help="Path to Layer 0 CSV directory")
    parser.add_argument("--with-tasks", action="store_true", help="Also seed maintenance tasks")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic generator instead of Layer 0 CSVs")
    parser.add_argument("--task-limit", type=int, default=None, help="Max tasks to load from Layer 0")
    parser.add_argument("--no-opt", action="store_true", help="Skip initial optimization")
    args = parser.parse_args()

    layer0 = _resolve_layer0_dir(args.layer0)
    if not layer0 and not args.synthetic:
        layer0 = _resolve_layer0_dir(None)

    seed_database(
        seed=args.seed,
        run_initial_optimization=not args.no_opt,
        layer0_dir=layer0,
        with_tasks=args.with_tasks,
        with_synthetic=args.synthetic,
        task_limit=args.task_limit,
    )


if __name__ == "__main__":
    main()
