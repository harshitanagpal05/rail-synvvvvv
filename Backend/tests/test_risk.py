"""Tests for risk prediction endpoints."""

from __future__ import annotations


def test_get_risk_segments_list(client):
    response = client.get("/risk/segments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    for item in data:
        assert "segment_id" in item
        assert "risk_30d" in item
        assert "confidence" in item
        assert 0.0 <= item["risk_30d"] <= 1.0


def test_get_single_segment_risk(client):
    response = client.get("/risk/SEG-TEST-001")
    assert response.status_code == 200
    data = response.json()
    assert data["segment_id"] == "SEG-TEST-001"
    assert "risk_30d" in data
    assert "expected_downtime_days" in data
    assert "survival_curve" in data
    assert len(data["survival_curve"]) > 0
    assert "feature_contributions" in data
    assert len(data["feature_contributions"]) > 0


def test_get_non_existent_segment_risk_returns_404(client):
    response = client.get("/risk/NON-EXISTENT")
    assert response.status_code == 404
