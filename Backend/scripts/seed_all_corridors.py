"""Seed all 6 Indian Railway Corridors into RailSync Database.

Generates realistic segments, Layer 1 Weibull risk predictions, and maintenance tasks
for Delhi-Mumbai, Delhi-Howrah, Chennai-Mumbai, Delhi-Chennai, Howrah-Mumbai, Howrah-Chennai.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR.parent))

from app.core.logging import get_logger
from app.db.database import get_session_factory
from app.db import repositories as repo
from app.db.models import Segment, MaintenanceTask, RiskPrediction
from app.integrations import layer1
from railsync.layer0.corridors import (
    CORRIDORS,
    ASSET_TYPES,
    CURVE_GRADIENT_CLASSES,
    MONSOON_EXPOSURE_LEVELS,
    FREIGHT_DENSITY_CLASSES,
    TASK_TYPES_BY_DEPT,
)

log = get_logger("seed_all_corridors")

def seed_corridors(segments_per_corridor: int = 20):
    session_factory = get_session_factory()
    session = session_factory()
    rng = random.Random(2026)

    try:
        log.info("Starting comprehensive seeding for all 6 National Corridors...")
        seg_idx = 1
        all_segments = []

        for corridor_key, corridor in CORRIDORS.items():
            divisions = corridor["divisions"]
            total_km = corridor["total_km"]
            km_per_seg = total_km / segments_per_corridor
            corridor_name = corridor["name"]

            for i in range(segments_per_corridor):
                div = divisions[i * len(divisions) // segments_per_corridor]
                age = round(rng.uniform(3, 42), 1)
                install_year = 2026 - int(age)

                seg_data = {
                    "segment_id": f"SEG-{seg_idx:03d}",
                    "division": div,
                    "section": f"{div}-Sec{((i % 5) + 1)}",
                    "corridor": corridor_name,
                    "asset_type": rng.choice(ASSET_TYPES),
                    "length_km": round(km_per_seg + rng.uniform(-4, 4), 1),
                    "age_years": age,
                    "installation_year": install_year,
                    "curve_gradient_class": rng.choice(CURVE_GRADIENT_CLASSES),
                    "monsoon_exposure": "high" if div in ["Mumbai", "Chennai", "Howrah", "Bhubaneswar", "Visakhapatnam"] else rng.choice(MONSOON_EXPOSURE_LEVELS),
                    "freight_density_class": rng.choice(FREIGHT_DENSITY_CLASSES),
                }
                all_segments.append(seg_data)
                seg_idx += 1

        inserted_segments = 0
        for s in all_segments:
            existing = repo.get_segment(session, s["segment_id"])
            if not existing:
                repo.upsert_segment(session, **s)
                inserted_segments += 1
            else:
                existing.corridor = s["corridor"]
                existing.division = s["division"]
                existing.section = s["section"]
                existing.monsoon_exposure = s["monsoon_exposure"]
        
        session.commit()
        log.info(f"Populated {len(all_segments)} segments ({inserted_segments} new) across {len(CORRIDORS)} corridors.")

        stored_risks = 0
        for s in all_segments:
            risk_pred = layer1.predict_risk(s)
            repo.save_risk_prediction(session, **{
                "segment_id": s["segment_id"],
                "risk_30d": risk_pred["risk_30d"],
                "expected_downtime_days": risk_pred["expected_downtime_days"],
                "preventive_block_duration_hrs": risk_pred["preventive_block_duration_hrs"],
                "confidence": risk_pred["confidence"],
                "overrun_probability": risk_pred.get("overrun_probability"),
                "cold_start_fallback": risk_pred.get("cold_start_fallback", False),
                "survival_curve": risk_pred.get("survival_curve"),
                "feature_contributions": risk_pred.get("feature_contributions"),
                "model_version": risk_pred.get("model_version"),
            })
            stored_risks += 1
            
        session.commit()
        log.info(f"Generated and saved {stored_risks} Layer 1 risk predictions.")

        task_idx = 1
        now = datetime.now()
        tasks_created = 0

        dept_list = ["TRACK", "OHE", "SIG", "TELE", "BRIDGE"]
        for s in all_segments:
            if rng.random() < 0.55:
                dept = rng.choice(dept_list)
                task_type = rng.choice(TASK_TYPES_BY_DEPT[dept])
                planned_duration = round(rng.uniform(1.5, 4.5), 1)
                crit = rng.choices([1, 2, 3, 4, 5], weights=[0.05, 0.15, 0.40, 0.30, 0.10])[0]

                task_data = {
                    "task_id": f"TSK-2026-{task_idx:04d}",
                    "segment_id": s["segment_id"],
                    "department": dept,
                    "task_type": task_type,
                    "claimed_criticality": crit,
                    "min_duration_hrs": planned_duration,
                    "preferred_window_start": now + timedelta(days=rng.randint(0, 5), hours=rng.randint(1, 12)),
                    "preferred_window_end": now + timedelta(days=rng.randint(6, 14)),
                    "planned_duration_hrs": planned_duration,
                    "actual_duration_hrs": None,
                    "overdue": crit <= 2 and rng.random() < 0.3,
                    "status": "pending",
                }
                
                if not repo.get_task(session, task_data["task_id"]):
                    repo.upsert_task(session, **task_data)
                    tasks_created += 1
                task_idx += 1

        session.commit()
        print(f"SUCCESS: Seeded {len(all_segments)} segments and {tasks_created} tasks across all 6 corridors!")
    except Exception as e:
        session.rollback()
        log.error(f"Seeding failed: {e}", exc_info=True)
        print(f"ERROR: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_corridors()
