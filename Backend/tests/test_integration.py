"""End-to-end integration test for RailSync 2.0 full pipeline.

Tests the entire lifecycle:
1. Ingest tasks across multiple departments
2. Predict segment risk via Layer 1
3. Run Layer 2 multi-department negotiation
4. Run Layer 3 CP-SAT optimization to generate weekly block plan
5. Verify explanation metadata on assignments
6. Run what-if disruption simulation (Plan B)
7. Record execution feedback and verify metrics loop
"""

from __future__ import annotations

from datetime import datetime, timedelta


def test_full_railsync_pipeline_e2e(client):
    # Step 1: Health check
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] in ("ok", "healthy", "degraded")

    # Step 2: Ingest 3 tasks across departments
    task_1 = {
        "task_id": "TASK-E2E-001",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Deep Screening",
        "claimed_criticality": 4,
        "min_duration_hrs": 3.0,
    }
    task_2 = {
        "task_id": "TASK-E2E-002",
        "segment_id": "SEG-TEST-001",
        "department": "OHE",
        "task_type": "Cantilever Adjustment",
        "claimed_criticality": 3,
        "min_duration_hrs": 2.0,
    }
    task_3 = {
        "task_id": "TASK-E2E-003",
        "segment_id": "SEG-TEST-002",
        "department": "SIG",
        "task_type": "Track Circuit Replacement",
        "claimed_criticality": 5,
        "min_duration_hrs": 1.5,
    }

    for t in [task_1, task_2, task_3]:
        resp = client.post("/ingest/tasks", json=t)
        assert resp.status_code in (200, 201)

    # Step 3: Layer 1 Risk query
    risk_resp = client.get("/risk/SEG-TEST-001")
    assert risk_resp.status_code == 200
    risk_data = risk_resp.json()
    assert risk_data["segment_id"] == "SEG-TEST-001"
    assert "survival_curve" in risk_data

    # Step 4: Layer 2 Negotiation
    neg_resp = client.post("/negotiate")
    assert neg_resp.status_code == 200
    neg_data = neg_resp.json()
    assert len(neg_data["scored_tasks"]) >= 3

    # Step 5: Layer 3 Optimization
    opt_resp = client.post("/optimize", json={
        "policy": "balanced",
        "horizon": "weekly",
    })
    assert opt_resp.status_code == 200
    opt_data = opt_resp.json()
    assert opt_data["weekly_plan"] is not None
    plan_id = opt_data["weekly_plan"]["plan_id"]
    assignments = opt_data["assignments"]
    assert len(assignments) > 0

    # Step 6: Verify Plan Retrieval & Explanation metadata
    plan_resp = client.get("/plan/current")
    assert plan_resp.status_code == 200
    curr_plan = plan_resp.json()
    assert curr_plan["plan_id"] == plan_id
    assert curr_plan["is_current"] is True

    first_assignment = curr_plan["assignments"][0]
    assert "explanation" in first_assignment
    if first_assignment["explanation"]:
        assert "primary_reason" in first_assignment["explanation"]

    # Step 7: What-if disruption simulation
    whatif_resp = client.post("/optimize/whatif", json={
        "type": "urgent_track_defect",
        "segment_id": "SEG-TEST-001",
        "severity": "critical",
        "description": "Urgent track defect",
    })
    assert whatif_resp.status_code == 200
    whatif_data = whatif_resp.json()
    assert whatif_data["feasible"] is True
    assert "plan_b" in whatif_data

    # Step 8: Execution feedback & closed-loop metrics
    fb_resp = client.post("/feedback/block", json={
        "assignment_id": first_assignment["id"],
        "actual_start": datetime.utcnow().isoformat(),
        "actual_duration_hrs": first_assignment["duration_hrs"] + 0.5,
        "completion_status": "completed",
        "notes": "Completed with slight delay due to monsoon speed restriction",
    })
    assert fb_resp.status_code == 201

    metrics_resp = client.get("/feedback/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert metrics["total_executed_blocks"] >= 1
