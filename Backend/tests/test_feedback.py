"""Tests for execution feedback and metrics endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta


def test_feedback_and_metrics(client):
    # Ingest task & optimize to generate assignment
    client.post("/ingest/tasks", json={
        "task_id": "TASK-FB-01",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Ultrasonic Flaw Detection",
        "claimed_criticality": 3,
        "min_duration_hrs": 2.0,
    })
    opt_resp = client.post("/optimize", json={"horizon": "weekly", "policy": "balanced"})
    assert opt_resp.status_code == 200
    plan = opt_resp.json()
    assert len(plan["assignments"]) > 0
    assignment_id = plan["assignments"][0]["id"]

    # Record execution feedback
    feedback_payload = {
        "assignment_id": assignment_id,
        "actual_start": datetime.utcnow().isoformat(),
        "actual_duration_hrs": 2.5,
        "completion_status": "completed",
        "notes": "Slight overrun due to tool transit",
    }
    fb_resp = client.post("/feedback/block", json=feedback_payload)
    assert fb_resp.status_code == 201
    fb_data = fb_resp.json()
    assert fb_data["assignment_id"] == assignment_id
    assert fb_data["actual_duration_hrs"] == 2.5
    assert fb_data["overrun_hrs"] is not None

    # Retrieve feedback metrics
    metrics_resp = client.get("/feedback/metrics")
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert metrics_data["total_executed_blocks"] >= 1
    assert "average_duration_error" in metrics_data
    assert "trend" in metrics_data
