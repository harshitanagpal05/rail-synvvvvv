"""Tests for task ingestion endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta


def test_ingest_valid_task(client):
    task_payload = {
        "task_id": "TASK-T01",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Rail Replacement",
        "claimed_criticality": 4,
        "min_duration_hrs": 2.5,
        "preferred_window_start": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "preferred_window_end": (datetime.utcnow() + timedelta(days=1, hours=6)).isoformat(),
        "overdue": False,
    }

    response = client.post("/ingest/tasks", json=task_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == "TASK-T01"
    assert data["segment_id"] == "SEG-TEST-001"
    assert data["claimed_criticality"] == 4
    assert data["status"] == "pending"


def test_ingest_task_missing_segment_returns_404(client):
    task_payload = {
        "task_id": "TASK-T02",
        "segment_id": "NON-EXISTENT-SEG",
        "department": "TRACK",
        "task_type": "Tamping",
        "claimed_criticality": 3,
        "min_duration_hrs": 1.5,
    }

    response = client.post("/ingest/tasks", json=task_payload)
    detail = response.json()["detail"].lower()
    assert "not found" in detail or "does not exist" in detail


def test_ingest_task_idempotency_returns_200(client):
    task_payload = {
        "task_id": "TASK-T03",
        "segment_id": "SEG-TEST-001",
        "department": "OHE",
        "task_type": "Contact Wire Replacement",
        "claimed_criticality": 3,
        "min_duration_hrs": 2.0,
    }

    # First creation: 201
    resp1 = client.post("/ingest/tasks", json=task_payload)
    assert resp1.status_code == 201

    # Second submission (idempotent update): 200
    task_payload["claimed_criticality"] = 4
    resp2 = client.post("/ingest/tasks", json=task_payload)
    assert resp2.status_code == 200
    assert resp2.json()["claimed_criticality"] == 4
