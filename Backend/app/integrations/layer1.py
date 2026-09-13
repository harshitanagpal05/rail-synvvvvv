"""RailSync 2.0 — Layer 1 Integration Adapter: Trained Risk Prediction.

Loads trained forecasts from Railsync_Layer1_Complete/. Unseen segments use the
same Weibull AFT model trained in Layer 1 (not a standalone age formula).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from app.core.logging import get_logger

log = get_logger("layer1")

_CANDIDATE_DIRS = [
    Path(__file__).resolve().parent.parent.parent.parent / "Railsync_Layer1_Complete",
    Path("Railsync_Layer1_Complete"),
    Path("../Railsync_Layer1_Complete"),
]

_LAYER1_DIR: Optional[Path] = None
for cand in _CANDIDATE_DIRS:
    if cand.exists() and (cand / "final_failure_forecasts.csv").exists():
        _LAYER1_DIR = cand.resolve()
        break

_TRAINED_FORECASTS: Dict[str, Dict[str, Any]] = {}
_TRAINED_SURVIVAL_CURVES: Dict[str, List[Dict[str, Any]]] = {}
_FEATURE_CONTRIBUTIONS: List[Dict[str, Any]] = []
_AFT_MODEL = None
_AFT_COVARIATE_COLS: List[str] = []
_LOADED = False

_AFT_CATEGORICAL = ["asset_type", "division"]
_DEFAULT_REPAIR_DAYS = 4.0


def _encode_aft_features(row: dict, covariate_cols: list[str]) -> pd.DataFrame:
    df = pd.DataFrame([row])
    df = pd.get_dummies(df, columns=_AFT_CATEGORICAL, dtype=float)
    return df.reindex(columns=covariate_cols, fill_value=0)


def _weibull_risk_30d(aft, covariates: pd.DataFrame, elapsed_days: float = 0.0) -> float:
    t0 = max(float(elapsed_days), 0.0)
    sf = aft.predict_survival_function(covariates, times=[t0, t0 + 30])
    s0 = float(sf.iloc[0, 0])
    s30 = float(sf.iloc[1, 0])
    if s0 <= 1e-12:
        return 1.0
    return float(np.clip(1.0 - s30 / s0, 0.0, 1.0))


def _weibull_survival_curve(
    aft, covariates: pd.DataFrame, elapsed_days: float = 0.0, horizon_days: int = 30
) -> list[dict[str, Any]]:
    t0 = max(float(elapsed_days), 0.0)
    rel_days = np.arange(1, horizon_days + 1, dtype=float)
    times = t0 + rel_days
    sf = aft.predict_survival_function(covariates, times=[t0] + times.tolist())
    s0 = float(sf.iloc[0, 0])
    if s0 <= 1e-12:
        cond = np.zeros(horizon_days)
    else:
        cond = np.clip(sf.iloc[1:, 0].values / s0, 0.0, 1.0)
    return [
        {"day": int(d), "survival_probability": round(float(s), 6)}
        for d, s in zip(rel_days.astype(int), cond)
    ]


def _normalize_asset_type(val: str) -> str:
    s = str(val or "").strip().upper()
    if "TRACK" in s or "P-WAY" in s or "RAIL" in s or "CIVIL" in s:
        return "Track"
    if "OHE" in s or "TRD" in s or "TRACTION" in s or "ELEC" in s:
        return "Traction/OHE"
    if "SIG" in s or "TELE" in s or "S&T" in s or "S & T" in s:
        return "S&T"
    return "Track"


def _normalize_division(val: str) -> str:
    s = str(val or "").strip()
    div_map = {
        "pryj": "Allahabad",
        "ddu": "Mughal Sarai",
        "ald": "Allahabad",
        "ndls": "Delhi",
        "bct": "Mumbai",
        "cstm": "Mumbai",
        "hwh": "Howrah",
    }
    low = s.lower()
    if low in div_map:
        return div_map[low]
    return s.title()


def _segment_to_aft_row(segment: dict[str, Any]) -> dict[str, Any]:
    monsoon_exp = str(segment.get("monsoon_exposure", "low")).strip().lower()
    monsoon_default = 1.0 if monsoon_exp == "high" else (0.5 if monsoon_exp == "medium" else 0.0)
    monsoon_val = float(segment.get("monsoon_month", monsoon_default))

    return {
        "age_years": float(segment.get("age_years", 20.0)),
        "grade3_defects_previous_90d": float(segment.get("grade3_defects_previous_90d", 1.0)),
        "defect_count_prev_month": float(segment.get("defect_count_prev_month", 1.0)),
        "overdue_tasks_active": float(segment.get("overdue_tasks_active", 0.0)),
        "monsoon_month": monsoon_val,
        "asset_type": _normalize_asset_type(segment.get("asset_type", "Track")),
        "division": _normalize_division(segment.get("division", "Delhi")),
    }


def _calibrate_live_defect_risk(segment: dict[str, Any], raw_risk: float) -> float:
    # If the defect is actively reported, the base model prediction is too low.
    risk_floor = 0.05
    monsoon = str(segment.get("monsoon_exposure", "")).lower()
    age = float(segment.get("age_years", 0))
    defects = float(segment.get("defect_count_prev_month", 0))
    
    if monsoon == "high" and age > 20:
        risk_floor = max(risk_floor, 0.55)
    if monsoon == "high" or age > 25:
        risk_floor = max(risk_floor, 0.40)
    if monsoon == "medium" and age > 15:
        risk_floor = max(risk_floor, 0.25)
    if defects >= 1:
        risk_floor = max(risk_floor, 0.15)
        
    return max(raw_risk, risk_floor)

def _predict_weibull_cold_start(segment: dict[str, Any]) -> dict[str, Any]:
    """Cold-start via trained Weibull AFT (same model as Layer 1 training)."""
    sid = str(segment.get("segment_id") or segment.get("id") or "").strip()
    cov_row = _segment_to_aft_row(segment)

    if _AFT_MODEL is not None and _AFT_COVARIATE_COLS:
        X = _encode_aft_features(cov_row, _AFT_COVARIATE_COLS)
        elapsed = float(segment.get("elapsed_days", 0.0))
        risk_val = _weibull_risk_30d(_AFT_MODEL, X, elapsed)
        curve = _weibull_survival_curve(_AFT_MODEL, X, elapsed)
    else:
        log.warning("Weibull AFT model unavailable; using conservative prior for %s", sid)
        risk_val = 0.05
        curve = [
            {"day": d, "survival_probability": round(max(0.01, 1.0 - (d * risk_val / 30.0)), 4)}
            for d in range(1, 31)
        ]

    if segment.get("live_defect"):
        risk_val = _calibrate_live_defect_risk(segment, risk_val)
        
    exp_down = round(float(risk_val * _DEFAULT_REPAIR_DAYS), 3)
    prev_dur = round(float(2.0 + risk_val * 4.0), 2)
    overrun_p = round(float(min(0.95, max(0.05, 0.08 + risk_val * 0.25))), 4)

    return {
        "segment_id": sid,
        "division": str(segment.get("division", cov_row["division"])),
        "asset_type": str(segment.get("asset_type", cov_row["asset_type"])),
        "risk_30d": round(risk_val, 6),
        "expected_downtime_days": exp_down,
        "preventive_block_duration_hrs": prev_dur,
        "confidence": "low",
        "cold_start_fallback": True,
        "overrun_probability": overrun_p,
        "forecast_as_of": str(segment.get("forecast_as_of", "")),
        "survival_curve": curve,
        "feature_contributions": _FEATURE_CONTRIBUTIONS,
        "model_version": "weibull-aft-cold-start-v2.0",
    }


def _ensure_trained_data() -> None:
    global _LOADED, _TRAINED_FORECASTS, _TRAINED_SURVIVAL_CURVES
    global _FEATURE_CONTRIBUTIONS, _AFT_MODEL, _AFT_COVARIATE_COLS

    if _LOADED:
        return

    if _LAYER1_DIR is None:
        log.warning("Railsync_Layer1_Complete not found. Layer 1 cold-start only.")
        _LOADED = True
        return

    try:
        fc_file = _LAYER1_DIR / "final_failure_forecasts.csv"
        if fc_file.exists():
            df_fc = pd.read_csv(fc_file)
            for _, row in df_fc.iterrows():
                sid = str(row["segment_id"]).strip()
                if "risk_30d" in row and pd.notna(row["risk_30d"]):
                    risk_val = float(row["risk_30d"])
                elif "failure_probability_30d" in row and pd.notna(row["failure_probability_30d"]):
                    risk_val = float(row["failure_probability_30d"])
                else:
                    risk_val = float(row.get("risk_score", 0.0)) / 100.0

                _TRAINED_FORECASTS[sid] = {
                    "segment_id": sid,
                    "division": str(row.get("division", "Delhi")),
                    "asset_type": str(row.get("asset_type", "Track")),
                    "risk_30d": round(risk_val, 6),
                    "expected_downtime_days": round(float(row.get("expected_downtime_days", risk_val * _DEFAULT_REPAIR_DAYS)), 3),
                    "preventive_block_duration_hrs": round(float(row.get("preventive_block_duration_hrs", 4.0)), 2),
                    "confidence": str(row.get("confidence", "medium")),
                    "cold_start_fallback": bool(row.get("cold_start_fallback", False)),
                    "overrun_probability": round(float(row.get("overrun_probability", 0.15)), 4),
                    "forecast_as_of": str(row.get("forecast_as_of", "")),
                }
            log.info("Loaded %d trained forecasts from %s", len(_TRAINED_FORECASTS), fc_file.name)

        sc_file = _LAYER1_DIR / "segment_survival_curves.csv"
        if sc_file.exists():
            df_sc = pd.read_csv(sc_file)
            day_col = "forecast_day" if "forecast_day" in df_sc.columns else "day"
            for sid, group in df_sc.groupby("segment_id"):
                sid_str = str(sid).strip()
                _TRAINED_SURVIVAL_CURVES[sid_str] = [
                    {
                        "day": int(r[day_col]),
                        "survival_probability": round(float(r["survival_probability"]), 6),
                    }
                    for _, r in group.sort_values(day_col).iterrows()
                ]
            log.info("Loaded %d survival curves from %s", len(_TRAINED_SURVIVAL_CURVES), sc_file.name)

        fi_file = _LAYER1_DIR / "feature_importance.csv"
        if fi_file.exists():
            df_fi = pd.read_csv(fi_file)
            imp_col = "importance" if "importance" in df_fi.columns else "approx_hazard_ratio"
            _FEATURE_CONTRIBUTIONS = [
                {
                    "name": str(r["feature"]),
                    "value": round(float(abs(r[imp_col])), 4),
                    "contribution": round(float(abs(r[imp_col])), 4),
                }
                for _, r in df_fi.head(6).iterrows()
            ]

        model_path = _LAYER1_DIR / "models" / "weibull_aft.joblib"
        cols_path = _LAYER1_DIR / "models" / "weibull_covariate_columns.json"
        if model_path.exists() and cols_path.exists():
            _AFT_MODEL = joblib.load(model_path)
            _AFT_COVARIATE_COLS = json.loads(cols_path.read_text())
            log.info("Loaded Weibull AFT model for cold-start predictions")

        _LOADED = True
    except Exception as exc:
        log.error("Failed to load Layer 1 artifacts: %s", exc, exc_info=True)
        _LOADED = True


def predict_risk(segment: dict[str, Any]) -> dict[str, Any]:
    """Predict 30-day failure risk for a segment."""
    _ensure_trained_data()

    sid = str(segment.get("segment_id") or segment.get("id") or "").strip()

    if sid in _TRAINED_FORECASTS:
        item = dict(_TRAINED_FORECASTS[sid])
        item["survival_curve"] = _TRAINED_SURVIVAL_CURVES.get(sid, [])
        item["feature_contributions"] = _FEATURE_CONTRIBUTIONS
        item["model_version"] = "trained-layer1-v2.0"
        return item

    return _predict_weibull_cold_start(segment)


def predict_risk_batch(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [predict_risk(seg) for seg in segments]


def is_available() -> bool:
    _ensure_trained_data()
    return len(_TRAINED_FORECASTS) > 0 or _AFT_MODEL is not None

