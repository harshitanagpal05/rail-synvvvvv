"""RailSync 2.0 — Risk prediction service (Layer 1 orchestration)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db import repositories as repo
from app.integrations import layer1
from app.schemas.risk import RiskPredictionResponse, SegmentRiskSummary

log = get_logger("service.risk")


def get_all_segment_risks(db: Session) -> list[SegmentRiskSummary]:
    """Return latest risk for every segment. Compute if not cached."""
    segments = repo.get_all_segments(db)
    if not segments:
        return []

    # Check DB cache first
    cached = repo.get_all_latest_risks(db)
    cached_map = {r.segment_id: r for r in cached}

    results = []
    for seg in segments:
        if seg.segment_id in cached_map:
            r = cached_map[seg.segment_id]
        else:
            r = _compute_and_store(db, seg)

        results.append(SegmentRiskSummary(
            segment_id=r.segment_id,
            division=seg.division,
            corridor=seg.corridor,
            risk_30d=r.risk_30d,
            expected_downtime_days=r.expected_downtime_days,
            preventive_block_duration_hrs=r.preventive_block_duration_hrs,
            confidence=r.confidence,
            overrun_probability=r.overrun_probability,
            cold_start_fallback=r.cold_start_fallback,
        ))

    results.sort(key=lambda x: x.risk_30d, reverse=True)
    return results


def get_segment_risk(db: Session, segment_id: str) -> RiskPredictionResponse:
    """Detailed risk for a single segment."""
    seg = repo.get_segment(db, segment_id)
    if seg is None:
        raise ValueError(f"Segment {segment_id} not found")

    cached = repo.get_latest_risk(db, segment_id)
    if cached:
        return RiskPredictionResponse(
            segment_id=cached.segment_id,
            risk_30d=cached.risk_30d,
            expected_downtime_days=cached.expected_downtime_days,
            preventive_block_duration_hrs=cached.preventive_block_duration_hrs,
            confidence=cached.confidence,
            overrun_probability=cached.overrun_probability,
            cold_start_fallback=cached.cold_start_fallback,
            survival_curve=cached.survival_curve or [],
            feature_contributions=cached.feature_contributions or [],
            model_version=cached.model_version,
            prediction_timestamp=cached.prediction_timestamp,
        )

    pred = _compute_and_store(db, seg)
    return RiskPredictionResponse(
        segment_id=pred.segment_id,
        risk_30d=pred.risk_30d,
        expected_downtime_days=pred.expected_downtime_days,
        preventive_block_duration_hrs=pred.preventive_block_duration_hrs,
        confidence=pred.confidence,
        overrun_probability=pred.overrun_probability,
        cold_start_fallback=pred.cold_start_fallback,
        survival_curve=pred.survival_curve or [],
        feature_contributions=pred.feature_contributions or [],
        model_version=pred.model_version,
        prediction_timestamp=pred.prediction_timestamp,
    )


def get_risk_data_map(db: Session) -> dict[str, dict]:
    """Build segment_id → risk dict for Layer 2/3 consumption."""
    segments = repo.get_all_segments(db)
    result = {}
    for seg in segments:
        cached = repo.get_latest_risk(db, seg.segment_id)
        if cached:
            result[seg.segment_id] = {
                "risk_30d": cached.risk_30d,
                "expected_downtime_days": cached.expected_downtime_days,
                "preventive_block_duration_hrs": cached.preventive_block_duration_hrs,
                "confidence": cached.confidence,
                "overrun_probability": cached.overrun_probability,
                "cold_start_fallback": cached.cold_start_fallback,
                "survival_curve": cached.survival_curve or [],
                "feature_contributions": cached.feature_contributions or [],
            }
        else:
            pred_data = layer1.predict_risk(_segment_to_dict(seg))
            result[seg.segment_id] = pred_data
            repo.save_risk_prediction(db, **{
                "segment_id": seg.segment_id,
                "risk_30d": pred_data["risk_30d"],
                "expected_downtime_days": pred_data["expected_downtime_days"],
                "preventive_block_duration_hrs": pred_data["preventive_block_duration_hrs"],
                "confidence": pred_data["confidence"],
                "overrun_probability": pred_data.get("overrun_probability"),
                "cold_start_fallback": pred_data.get("cold_start_fallback", False),
                "survival_curve": pred_data.get("survival_curve"),
                "feature_contributions": pred_data.get("feature_contributions"),
                "model_version": pred_data.get("model_version"),
            })
    db.commit()
    return result


def _compute_and_store(db: Session, seg):
    seg_dict = _segment_to_dict(seg)
    pred_data = layer1.predict_risk(seg_dict)
    log.info("Risk computed segment=%s risk_30d=%.4f", seg.segment_id, pred_data["risk_30d"])

    pred = repo.save_risk_prediction(db, **{
        "segment_id": seg.segment_id,
        "risk_30d": pred_data["risk_30d"],
        "expected_downtime_days": pred_data["expected_downtime_days"],
        "preventive_block_duration_hrs": pred_data["preventive_block_duration_hrs"],
        "confidence": pred_data["confidence"],
        "overrun_probability": pred_data.get("overrun_probability"),
        "cold_start_fallback": pred_data.get("cold_start_fallback", False),
        "survival_curve": pred_data.get("survival_curve"),
        "feature_contributions": pred_data.get("feature_contributions"),
        "model_version": pred_data.get("model_version"),
    })
    db.commit()
    return pred


def _segment_to_dict(seg) -> dict:
    return {
        "segment_id": seg.segment_id,
        "age_years": seg.age_years,
        "length_km": seg.length_km,
        "curve_gradient_class": seg.curve_gradient_class,
        "monsoon_exposure": seg.monsoon_exposure,
        "freight_density_class": seg.freight_density_class,
    }
