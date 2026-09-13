"""Tests for Layer 2 negotiation endpoints."""

from __future__ import annotations


def test_negotiate_tasks_endpoint(client):
    # Ingest two tasks first
    client.post("/ingest/tasks", json={
        "task_id": "TASK-NEG-01",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Tamping",
        "claimed_criticality": 5,  # Potentially inflated
        "min_duration_hrs": 2.0,
    })
    client.post("/ingest/tasks", json={
        "task_id": "TASK-NEG-02",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Ballast Cleaning",
        "claimed_criticality": 2,
        "min_duration_hrs": 1.5,
    })

    response = client.post("/negotiate")
    assert response.status_code == 200
    data = response.json()
    assert "negotiation_run_id" in data
    assert "scored_tasks" in data
    assert len(data["scored_tasks"]) >= 2
    for t in data["scored_tasks"]:
        assert "evidence_score" in t
        assert "inflated_claim" in t
        assert "weighted_priority" in t
    assert "total_tasks" in data
