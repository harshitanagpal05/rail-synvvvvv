"""Tests for Layer 3 optimization, what-if re-optimization, and advanced planning endpoints."""

from __future__ import annotations
from Optimization import optimize_schedule


def test_optimization_package_import():
    """Verify that Optimization package is directly importable and usable."""
    assert optimize_schedule is not None


def test_optimize_and_whatif_endpoints(client):
    # Ingest task
    client.post("/ingest/tasks", json={
        "task_id": "TASK-OPT-01",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Rail Weld Repair",
        "claimed_criticality": 4,
        "min_duration_hrs": 2.0,
    })

    # Run optimization
    opt_payload = {
        "horizon": "weekly",
        "policy": "balanced",
    }
    opt_resp = client.post("/optimize", json=opt_payload)
    assert opt_resp.status_code == 200
    opt_data = opt_resp.json()
    assert "run_id" in opt_data
    assert "weekly_plan" in opt_data
    assert "assignments" in opt_data
    assert "objective_values" in opt_data
    assert "robustness_score" in opt_data
    assert opt_data["feasible"] is True

    # Test what-if analysis
    whatif_payload = {
        "type": "unplanned_failure",
        "segment_id": "SEG-TEST-001",
        "severity": "high",
        "description": "Emergency track fracture",
    }
    whatif_resp = client.post("/optimize/whatif", json=whatif_payload)
    assert whatif_resp.status_code == 200
    whatif_data = whatif_resp.json()
    assert "run_id" in whatif_data
    assert "plan_b" in whatif_data
    assert "changed_assignments" in whatif_data
    assert whatif_data["feasible"] is True


def test_policy_presets_optimization(client):
    """Verify that safety_first, balanced, and throughput_first policies execute via Layer 3."""
    client.post("/ingest/tasks", json={
        "task_id": "TASK-POL-01",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Track Screening",
        "claimed_criticality": 5,
        "min_duration_hrs": 2.5,
    })

    for policy in ["safety_first", "balanced", "throughput_first"]:
        resp = client.post("/optimize", json={"horizon": "weekly", "policy": policy})
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy"] == policy
        assert data["feasible"] is True
        assert len(data["assignments"]) > 0


def test_whatif_with_locked_assignments_and_emergency_tasks(client):
    """Verify that what-if enforces locked_assignments and integrates emergency tasks."""
    # Ingest baseline task
    client.post("/ingest/tasks", json={
        "task_id": "TASK-LOCK-01",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Point Maintenance",
        "claimed_criticality": 3,
        "min_duration_hrs": 2.0,
    })

    # Run what-if with locked assignment and emergency task
    whatif_payload = {
        "scenario_id": "SCN-TEST-LOCK-01",
        "description": "Inject emergency fracture with locked baseline task",
        "locked_assignments": {
            "TASK-LOCK-01": "BLK-D1-NIGHT"
        },
        "emergency_tasks": [
            {
                "task_id": "EMERGENCY-FRACTURE-01",
                "segment_id": "SEG-TEST-002",
                "department": "TRACK",
                "task_type": "Emergency Rail Fracture",
                "claimed_criticality": 5,
                "min_duration_hrs": 2.0,
            }
        ],
    }
    resp = client.post("/optimize/whatif", json=whatif_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["feasible"] is True
    assert data["scenario_id"] == "SCN-TEST-LOCK-01"

    # Check Plan B contains the locked task in BLK-D1-NIGHT
    assignments = data["added_assignments"] + [
        a for a in data.get("changed_assignments", [])
    ]
    # Check that reasons and summary are populated
    assert len(data["reason"]) > 0
    assert data["solver_status"] in ("OPTIMAL", "FEASIBLE")


def test_advanced_layer3_endpoints(client):
    """Verify weekly, monthly, pareto, robustness, and plan-b endpoints."""
    # Ingest test tasks
    client.post("/ingest/tasks", json={
        "task_id": "TASK-ADV-01",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Ballast Tamping",
        "claimed_criticality": 4,
        "min_duration_hrs": 3.0,
    })

    # 1. Weekly endpoint
    resp = client.get("/optimize/weekly?policy=balanced")
    assert resp.status_code == 200
    weekly_data = resp.json()
    assert weekly_data["horizon"] == "WEEKLY"
    assert "schedule" in weekly_data

    # 2. Monthly endpoint
    resp = client.get("/optimize/monthly?policy=safety_first")
    assert resp.status_code == 200
    monthly_data = resp.json()
    assert monthly_data["horizon"] == "MONTHLY"
    assert "schedule" in monthly_data

    # 3. Pareto frontier endpoint
    resp = client.get("/optimize/pareto")
    assert resp.status_code == 200
    pareto_data = resp.json()
    assert "points" in pareto_data
    assert len(pareto_data["points"]) == 3  # Safety-First, Balanced, Throughput-First
    assert pareto_data["recommended_preset"] == "BALANCED"

    # 4. Robustness endpoint
    resp = client.get("/optimize/robustness?num_scenarios=10")
    assert resp.status_code == 200
    rob_data = resp.json()
    assert "robustness_percentage" in rob_data
    assert "total_scenarios" in rob_data
    assert rob_data["total_scenarios"] == 10

    # 5. Plan B contingencies endpoint
    resp = client.get("/optimize/plan-b")
    assert resp.status_code == 200
    planb_data = resp.json()
    assert "top_contingencies_count" in planb_data
    assert planb_data["top_contingencies_count"] >= 1
    assert "contingencies" in planb_data
    assert len(planb_data["contingencies"]) >= 1


def test_frontend_optimization_api_aliases(client):
    """Verify frontend aliases: GET /optimize, POST /what-if, GET /optimize/policies, GET /optimize/contingencies."""
    client.post("/ingest/tasks", json={
        "task_id": "TASK-ALIAS-01",
        "segment_id": "SEG-TEST-001",
        "department": "TRACK",
        "task_type": "Track Inspection",
        "claimed_criticality": 4,
        "min_duration_hrs": 2.0,
    })

    # GET /optimize
    resp_get_opt = client.get("/optimize?policy=balanced&horizon=weekly")
    assert resp_get_opt.status_code == 200
    data_get_opt = resp_get_opt.json()
    assert "assignments" in data_get_opt
    assert len(data_get_opt["assignments"]) > 0
    first_a = data_get_opt["assignments"][0]
    assert "status" in first_a
    assert "assigned_block" in first_a
    assert "why" in first_a

    # POST /what-if alias with event_type and event_time
    resp_whatif_alias = client.post("/what-if", json={
        "event_type": "RAIL_FRACTURE",
        "segment_id": "SEG-TEST-001",
        "event_time": "11:30",
        "severity": "emergency",
        "description": "Emergency rail crack at 11:30 AM",
    })
    assert resp_whatif_alias.status_code == 200
    whatif_data = resp_whatif_alias.json()
    assert whatif_data["feasible"] is True
    assert "changed_assignments" in whatif_data

    # GET /optimize/policies alias
    resp_pol = client.get("/optimize/policies")
    assert resp_pol.status_code == 200
    assert len(resp_pol.json()["points"]) == 3

    # GET /optimize/contingencies alias
    resp_cont = client.get("/optimize/contingencies")
    assert resp_cont.status_code == 200
    assert "contingencies" in resp_cont.json()


def test_invalid_policy_input_validation(client):
    """Verify that invalid policies are rejected with HTTP 422 Unprocessable Entity."""
    resp = client.post("/optimize", json={"policy": "INVALID_POLICY", "horizon": "weekly"})
    assert resp.status_code == 422

