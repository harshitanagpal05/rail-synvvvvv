"""Tests for GET /health endpoint."""

from __future__ import annotations


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "healthy", "degraded")
    assert "layer1" in data
    assert "layer2" in data
    assert "layer3" in data
    assert "timestamp" in data
