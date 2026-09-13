"""RailSync 2.0 — Real Data Loader for Supabase PostgreSQL.

One-shot CLI to load Layer 0/1/2 CSV artifacts into Supabase. Not invoked on
backend startup — run explicitly when you want a full corridor reload.

    python -m app.load_real_data
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
import pandas as pd
from sqlalchemy import text

from app.core.logging import get_logger
from app.db import repositories as repo
from app.db.database import get_session_factory
from app.integrations import layer1
from app.services import optimization_service

log = get_logger("loader")


def clear_dummy_data(session) -> None:
    """Safely truncate/delete all existing demo tables in reverse FK dependency order."""
    log.info("Deleting existing dummy/demo data from Supabase tables...")
    tables = [
        "feedback_records",
        "block_assignments",
        "block_plans",
        "optimization_runs",
        "negotiation_results",
        "risk_predictions",
        "maintenance_tasks",
        "segments",
    ]
    for tbl in tables:
        session.execute(text(f"DELETE FROM {tbl}"))
        log.info("Deleted all rows from %s", tbl)
    session.commit()
    log.info("All demo data deleted successfully.")


def load_real_segments(session, base_dir: str = ".") -> int:
    """Load all segments from segments_master.csv without modification."""
    path = os.path.join(base_dir, "Railsync_2.0_Layer_0_FINAL", "segments_master.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Segments master file not found: {path}")

    df = pd.read_csv(path)
    count = 0
    for _, row in df.iterrows():
        repo.upsert_segment(
            session,
            segment_id=str(row["id"]),
            division=str(row["division"]),
            asset_type=str(row["asset_type"]),
            length_km=float(row["length_km"]),
            age_years=float(row["age_years"]),
            installation_year=int(row["installation_year"]) if pd.notna(row.get("installation_year")) else None,
            curve_gradient_class=str(row.get("curve_gradient_class", "Low-Flat")),
            monsoon_exposure=str(row.get("monsoon_exposure", "Low")),
            freight_density_class=str(row.get("freight_density_class", "Low")),
            corridor=None,
            section=None,
        )
        count += 1

    session.commit()
    log.info("Inserted %d real segments into Supabase", count)
    return count


def load_real_tasks(session, base_dir: str = ".") -> int:
    """Load 602 maintenance tasks by combining Layer 0 tasks with Layer 2 scoring data."""
    tasks_path = os.path.join(base_dir, "Railsync_2.0_Layer_0_FINAL", "maintenance_tasks.csv")
    l2_path = os.path.join(base_dir, "Railsync_Layer2_Outputs", "layer2_scored_task_pool.csv")

    df_tasks = pd.read_csv(tasks_path)
    df_l2 = pd.read_csv(l2_path)

    # Merge on task_id to get claimed_criticality and min_duration_hrs
    merged = pd.merge(df_tasks, df_l2[["task_id", "claimed_criticality", "min_duration_hrs", "preferred_window"]], on="task_id", how="left")

    count = 0
    for _, row in merged.iterrows():
        claimed_crit = int(row["claimed_criticality"]) if pd.notna(row.get("claimed_criticality")) else 3
        min_dur = float(row["min_duration_hrs"]) if pd.notna(row.get("min_duration_hrs")) else float(row["planned_duration_hrs"])
        overdue_bool = bool(int(row["overdue_flag"]) == 1) if pd.notna(row.get("overdue_flag")) else False

        repo.upsert_task(
            session,
            task_id=str(row["task_id"]),
            segment_id=str(row["segment_id"]),
            department=str(row["department"]),
            task_type=str(row["type"]),
            claimed_criticality=claimed_crit,
            min_duration_hrs=min_dur,
            planned_duration_hrs=float(row["planned_duration_hrs"]) if pd.notna(row.get("planned_duration_hrs")) else None,
            actual_duration_hrs=float(row["actual_duration_hrs"]) if pd.notna(row.get("actual_duration_hrs")) else None,
            overdue=overdue_bool,
            status="pending",
        )
        count += 1

    session.commit()
    log.info("Inserted %d real maintenance tasks into Supabase", count)
    return count


def load_real_negotiation_results(session, base_dir: str = ".") -> int:
    """Load 602 Layer 2 negotiation records from layer2_scored_task_pool.csv."""
    l2_path = os.path.join(base_dir, "Railsync_Layer2_Outputs", "layer2_scored_task_pool.csv")
    df_l2 = pd.read_csv(l2_path)

    run_id = "NEG-L2-OFFICIAL"
    count = 0
    for _, row in df_l2.iterrows():
        repo.save_negotiation_result(
            session,
            task_id=str(row["task_id"]),
            evidence_score=float(row["evidence_score"]),
            inflated_claim=bool(row["inflated_claim"]),
            weighted_priority=float(row["priority_score"]),
            consolidation_group=str(row["segment_group"]) if pd.notna(row.get("segment_group")) else None,
            negotiation_run_id=run_id,
        )
        count += 1

    session.commit()
    log.info("Inserted %d Layer 2 negotiation results into Supabase", count)
    return count


def load_real_risk_predictions(session, base_dir: str = ".") -> tuple[int, list[str]]:
    """Store Layer 1 predictions via the same adapter used at runtime."""
    seg_path = os.path.join(base_dir, "Railsync_2.0_Layer_0_FINAL", "segments_master.csv")
    df_seg = pd.read_csv(seg_path)

    count = 0
    loaded_segs: list[str] = []
    for _, row in df_seg.iterrows():
        segment = {
            "segment_id": str(row["id"]),
            "division": str(row["division"]),
            "asset_type": str(row["asset_type"]),
            "age_years": float(row["age_years"]),
        }
        pred = layer1.predict_risk(segment)
        repo.save_risk_prediction(
            session,
            segment_id=segment["segment_id"],
            risk_30d=pred["risk_30d"],
            expected_downtime_days=pred["expected_downtime_days"],
            preventive_block_duration_hrs=pred["preventive_block_duration_hrs"],
            confidence=pred["confidence"],
            survival_curve=pred.get("survival_curve"),
            feature_contributions=pred.get("feature_contributions"),
            model_version=pred.get("model_version"),
        )
        loaded_segs.append(segment["segment_id"])
        count += 1

    session.commit()
    log.info("Inserted %d Layer 1 risk predictions into Supabase", count)
    return count, loaded_segs


def main():
    session_factory = get_session_factory()
    session = session_factory()
    try:
        print("=== Step 1: Deleting existing dummy demo data ===")
        clear_dummy_data(session)

        print("\n=== Step 2: Loading Real Segments ===")
        seg_count = load_real_segments(session)

        print("\n=== Step 3: Loading Real Maintenance Tasks ===")
        task_count = load_real_tasks(session)

        print("\n=== Step 4: Loading Layer 2 Negotiation Results ===")
        neg_count = load_real_negotiation_results(session)

        print("\n=== Step 5: Loading Layer 1 Risk Predictions & Survival Curves ===")
        risk_count, loaded_segs = load_real_risk_predictions(session)

        print("\n=== Step 6: Generating Initial Layer 3 Baseline Optimization Plan ===")
        opt_resp = optimization_service.run_optimization(session, policy="balanced", horizon="weekly")
        print(f"Baseline Optimization Plan Created: {opt_resp.run_id}")
        print(f"Status: {opt_resp.status}, Total Assignments: {opt_resp.total_assignments}")

        print("\n=== All Real Data Successfully Loaded into Supabase! ===")

    except Exception as e:
        session.rollback()
        log.error("Data loading failed: %s", e, exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
