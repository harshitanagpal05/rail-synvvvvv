"""Tests for Layer 1 trained ML runtime adapter and Weibull cold-start."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.integrations import layer1, layer3
from Optimization import MaintenanceTask

_LAYER1_DIR = Path(__file__).resolve().parents[2] / "Railsync_Layer1_Complete"


def _forecasts_path() -> Path:
    return _LAYER1_DIR / "final_failure_forecasts.csv"


@pytest.fixture(scope="module")
def forecasts_df():
    path = _forecasts_path()
    if not path.exists():
        pytest.skip("Railsync_Layer1_Complete forecasts not found")
    return pd.read_csv(path)


def test_trained_layer1_prediction_matches_artifacts(forecasts_df):
    for seg_id in ("SEG-002", "SEG-039", "SEG-043"):
        if seg_id not in forecasts_df["segment_id"].values:
            pytest.skip(f"{seg_id} not in trained forecasts")
        expected = forecasts_df.loc[forecasts_df["segment_id"] == seg_id].iloc[0]
        res = layer1.predict_risk({"segment_id": seg_id})
        assert res["segment_id"] == seg_id
        assert res["risk_30d"] == pytest.approx(float(expected["risk_30d"]), rel=1e-4)
        assert res["cold_start_fallback"] is False
        assert res["model_version"] == "trained-layer1-v2.0"
        assert res["risk_30d"] < 0.95  # no pegged 100% probabilities


def test_no_standalone_age_formula_for_known_segments(forecasts_df):
    row = forecasts_df.loc[forecasts_df["segment_id"] == "SEG-002"].iloc[0]
    res = layer1.predict_risk({"segment_id": "SEG-002", "age_years": 10})
    assert res["risk_30d"] == pytest.approx(float(row["risk_30d"]), rel=1e-4)


def test_survival_curve_is_trained_output():
    res = layer1.predict_risk({"segment_id": "SEG-002"})
    curve = res["survival_curve"]
    if not curve:
        pytest.skip("No survival curve loaded for SEG-002")
    assert len(curve) == 30
    assert curve[0]["day"] == 1
    assert 0.0 < curve[0]["survival_probability"] <= 1.0
    assert curve[-1]["day"] == 30


def test_cold_start_uses_weibull_not_age_formula():
    """Unseen segments must use trained Weibull AFT, not 0.05 + age/50*0.3."""
    res = layer1.predict_risk({
        "segment_id": "SEG-NEW-CORRIDOR-999",
        "age_years": 40,
        "asset_type": "Track",
        "division": "Delhi",
    })
    old_age_formula = round(min(0.99, max(0.01, 0.05 + (40 / 50.0) * 0.3)), 4)

    assert res["segment_id"] == "SEG-NEW-CORRIDOR-999"
    assert res["cold_start_fallback"] is True
    assert res["confidence"] == "low"
    assert res["model_version"] == "weibull-aft-cold-start-v2.0"
    assert abs(res["risk_30d"] - old_age_formula) > 0.05
    assert 0.0 <= res["risk_30d"] <= 1.0
    assert len(res["survival_curve"]) == 30


def test_batch_predictions(forecasts_df):
    batch = layer1.predict_risk_batch([{"segment_id": "SEG-002"}, {"segment_id": "SEG-043"}])
    assert len(batch) == 2
    for res, seg_id in zip(batch, ("SEG-002", "SEG-043")):
        expected = float(
            forecasts_df.loc[forecasts_df["segment_id"] == seg_id, "risk_30d"].iloc[0]
        )
        assert res["segment_id"] == seg_id
        assert res["risk_30d"] == pytest.approx(expected, rel=1e-4)


def test_layer1_to_backend_to_layer3(forecasts_df):
    trained_pred = layer1.predict_risk({"segment_id": "SEG-002"})
    risk_dict = {"SEG-002": trained_pred}
    task_dict = {"task_id": "TASK-SEG02", "segment_id": "SEG-002", "claimed_criticality": "HIGH"}

    task = layer3.transform_task(task_dict, risk_dict)
    assert isinstance(task, MaintenanceTask)
    assert task.segment == "SEG-002"
    assert task.risk_30d == trained_pred["risk_30d"]
    assert task.expected_downtime_days == trained_pred["expected_downtime_days"]
    assert task.cold_start_fallback is False
