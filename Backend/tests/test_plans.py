"""Tests for plan retrieval endpoints."""

from __future__ import annotations


def test_get_current_plan(client):
    # First optimize to have an active plan
    client.post("/ingest/tasks", json={
        "task_id": "TASK-PLAN-01",
        "segment_id": "SEG-TEST-001",
        "department": "SIG",
        "task_type": "Point Machine Overhaul",
        "claimed_criticality": 3,
        "min_duration_hrs": 1.5,
    })
    opt_resp = client.post("/optimize", json={"horizon": "weekly", "policy": "balanced"})
    assert opt_resp.status_code == 200
    created_plan_id = opt_resp.json()["weekly_plan"]["plan_id"]

    # Retrieve current plan
    current_resp = client.get("/plan/current")
    assert current_resp.status_code == 200
    plan_data = current_resp.json()
    assert plan_data["plan_id"] == created_plan_id
    assert plan_data["is_current"] is True
    assert "assignments" in plan_data

    # Retrieve by specific plan_id
    specific_resp = client.get(f"/plan/{created_plan_id}")
    assert specific_resp.status_code == 200
    assert specific_resp.json()["plan_id"] == created_plan_id


def test_get_non_existent_plan_returns_404(client):
    response = client.get("/plan/PLAN-DOES-NOT-EXIST")
    assert response.status_code == 404
