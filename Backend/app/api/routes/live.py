"""RailSync 2.0 — Live Defect Reporting, Risk Prediction, and Optimization Pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db import repositories as repo
from app.db.database import get_db
from app.integrations import layer1, layer2, layer3
from app.services import optimization_service, risk_service, task_service

log = get_logger("route.live")

router = APIRouter(prefix="/live", tags=["Live Defect & Optimization"])


class LivePredictRequest(BaseModel):
    age_years: float = Field(..., ge=0.0, le=100.0, description="Asset age in years")
    installation_year: Optional[int] = Field(None, ge=1950, le=2030, description="Installation year")
    length_km: float = Field(..., gt=0.0, le=100.0, description="Segment length in km")
    monsoon_exposure: str = Field(..., description="Monsoon exposure: low, medium, high")
    asset_type: str = Field(..., description="Asset type: TRACK, OHE, SIG, TELE, BRIDGE")
    division: str = Field(..., description="Railway division, e.g. Delhi, Mumbai, Allahabad")
    segment_id: Optional[str] = Field(None, description="Optional custom segment ID")
    corridor: Optional[str] = Field("Delhi-Howrah", description="Railway corridor")


class LiveReportOptimizeRequest(BaseModel):
    age_years: float = Field(..., ge=0.0, le=100.0)
    installation_year: Optional[int] = Field(None, ge=1950, le=2030)
    length_km: float = Field(..., gt=0.0, le=100.0)
    monsoon_exposure: str = Field(..., description="low, medium, high")
    asset_type: str = Field(...)
    division: str = Field(...)
    segment_id: Optional[str] = None
    corridor: Optional[str] = "Delhi-Howrah"
    task_type: Optional[str] = "Emergency Defect Rectification"
    claimed_criticality: Optional[int] = Field(5, ge=1, le=5)
    department: Optional[str] = None
    policy: Optional[str] = Field("balanced", description="safety_first, balanced, throughput_first")
    horizon: Optional[str] = Field("weekly", description="weekly, monthly, both")


@router.post("/predict", summary="Predict Failure Risk for Live Defect")
def predict_live_risk(request: LivePredictRequest):
    """Layer 1 Failure Risk Forecast on arbitrary user-reported defect parameters."""
    seg_id = request.segment_id or f"LIVE-{request.division[:3].upper()}-{request.asset_type[:3].upper()}-{uuid.uuid4().hex[:4].upper()}"

    payload = {
        "segment_id": seg_id,
        "age_years": request.age_years,
        "installation_year": request.installation_year or (2026 - int(request.age_years)),
        "length_km": request.length_km,
        "monsoon_exposure": request.monsoon_exposure,
        "asset_type": request.asset_type,
        "division": request.division,
        "grade3_defects_previous_90d": 3.0,
        "defect_count_prev_month": 2.0,
        "live_defect": True,
    }

    try:
        prediction = layer1.predict_risk(payload)
        prediction["segment_id"] = seg_id
        prediction["division"] = request.division
        prediction["asset_type"] = request.asset_type
        return prediction
    except Exception as exc:
        log.error("Live risk prediction failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk prediction failed: {str(exc)}",
        )


@router.post("/report-and-optimize", summary="Report Live Defect & Run Full Optimization Pipeline")
def report_and_optimize(request: LiveReportOptimizeRequest, db: Session = Depends(get_db)):
    """End-to-end pipeline: Ingest live defect -> Layer 1 Risk -> Layer 2 Negotiation -> Layer 3 CP-SAT Optimization."""
    try:
        div_clean = request.division.strip()
        asset_clean = request.asset_type.strip().upper()
        seg_id = request.segment_id or f"LIVE-{div_clean[:3].upper()}-{asset_clean[:3].upper()}-{uuid.uuid4().hex[:4].upper()}"

        # 1. Map department
        if request.department:
            dept = request.department.upper()
        elif "TRACK" in asset_clean or "P-WAY" in asset_clean or "RAIL" in asset_clean:
            dept = "TRACK"
        elif "OHE" in asset_clean or "TRD" in asset_clean or "TRACTION" in asset_clean or "ELEC" in asset_clean:
            dept = "OHE"
        elif "SIG" in asset_clean or "S&T" in asset_clean:
            dept = "SIG"
        elif "TELE" in asset_clean:
            dept = "TELE"
        else:
            dept = "TRACK"

        install_yr = request.installation_year or (2026 - int(request.age_years))

        # 2. Upsert Segment
        segment_obj = repo.upsert_segment(
            db,
            segment_id=seg_id,
            division=div_clean.title(),
            section=f"{div_clean.title()}-Sec-Live",
            corridor=request.corridor or "Delhi-Howrah",
            asset_type=dept,
            length_km=request.length_km,
            age_years=request.age_years,
            installation_year=install_yr,
            curve_gradient_class="moderate",
            monsoon_exposure=request.monsoon_exposure.lower(),
            freight_density_class="high",
        )

        # 3. Layer 1 Risk Prediction
        risk_input = {
            "segment_id": seg_id,
            "age_years": request.age_years,
            "installation_year": install_yr,
            "length_km": request.length_km,
            "monsoon_exposure": request.monsoon_exposure,
            "asset_type": dept,
            "division": div_clean,
            "grade3_defects_previous_90d": 3.0,
            "defect_count_prev_month": 2.0,
            "live_defect": True,
        }
        risk_pred = layer1.predict_risk(risk_input)

        repo.save_risk_prediction(
            db,
            segment_id=seg_id,
            risk_30d=risk_pred["risk_30d"],
            expected_downtime_days=risk_pred["expected_downtime_days"],
            preventive_block_duration_hrs=risk_pred["preventive_block_duration_hrs"],
            confidence=risk_pred["confidence"],
            survival_curve=risk_pred.get("survival_curve"),
            feature_contributions=risk_pred.get("feature_contributions"),
            model_version=risk_pred.get("model_version"),
        )

        # 4. Ingest Maintenance Task for this live defect
        task_id = f"TSK-LIVE-{uuid.uuid4().hex[:6].upper()}"
        min_duration = float(risk_pred.get("preventive_block_duration_hrs", 3.0))
        now = datetime.utcnow()

        task_obj, _ = repo.upsert_task(
            db,
            task_id=task_id,
            segment_id=seg_id,
            department=dept,
            task_type=request.task_type or "Emergency Defect Rectification",
            claimed_criticality=request.claimed_criticality or 5,
            min_duration_hrs=min_duration,
            preferred_window_start=now,
            preferred_window_end=now + timedelta(days=7),
            planned_duration_hrs=min_duration,
            overdue=(request.claimed_criticality or 5) >= 4,
            status="pending",
        )
        db.commit()

        # 5. Run Optimization Service (Layer 2 Negotiation + Layer 3 CP-SAT Optimization)
        opt_response = optimization_service.run_optimization(
            db=db,
            policy=request.policy or "balanced",
            horizon=request.horizon or "weekly",
        )

        # 6. Locate our newly scheduled assignment and negotiation result
        live_assignment = None
        for a in opt_response.assignments:
            if a.task_id == task_id or a.segment_id == seg_id:
                live_assignment = a.model_dump(mode="json")
                break

        # Check negotiation result
        neg_item = None
        db_neg = repo.get_negotiation_result(db, task_id) if hasattr(repo, "get_negotiation_result") else None
        if db_neg:
            neg_item = {
                "evidence_score": db_neg.evidence_score,
                "inflated_claim": db_neg.inflated_claim,
                "weighted_priority": db_neg.weighted_priority,
                "consolidation_group": db_neg.consolidation_group,
            }
        else:
            # Reconstruct from layer2 formula if needed
            ev = round(min(float(risk_pred["risk_30d"]) * 5.0 + 0.8, 5.0), 3)
            claimed = request.claimed_criticality or 5
            inflated = (claimed / ev) > 1.5 if ev >= 0.5 else claimed >= 3
            neg_item = {
                "evidence_score": ev,
                "inflated_claim": inflated,
                "weighted_priority": round(ev * 0.4 + float(risk_pred["risk_30d"]) * 3.0, 3),
            }

        return {
            "status": "success",
            "task_id": task_id,
            "segment_id": seg_id,
            "segment": {
                "segment_id": seg_id,
                "division": div_clean.title(),
                "asset_type": dept,
                "length_km": request.length_km,
                "age_years": request.age_years,
                "installation_year": install_yr,
                "monsoon_exposure": request.monsoon_exposure,
            },
            "risk_prediction": risk_pred,
            "negotiation": {
                "claimed_criticality": request.claimed_criticality or 5,
                **neg_item,
            },
            "optimization": {
                "run_id": opt_response.run_id,
                "policy": opt_response.policy,
                "status": opt_response.status,
                "feasible": opt_response.feasible,
                "total_assignments": len(opt_response.assignments),
                "execution_time_ms": opt_response.execution_time_ms,
                "scheduled_assignment": live_assignment,
            },
        }

    except Exception as exc:
        db.rollback()
        log.error("Live report and optimize failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Live reporting and optimization pipeline error: {str(exc)}",
        )
