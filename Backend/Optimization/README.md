# RailSync Layer 3: Optimization Engine 🚂⚡
### Team Integration & Technical Handoff Guide

> **Project:** AI-Powered Automatic Block Planning & Digital Twin for Indian Railways  
> **Module:** Layer 3 - Maintenance Block Optimization Engine  
> **Technology:** Python, Google OR-Tools CP-SAT (Constraint Programming with Satisfiability)

---

## 📌 1. What This Module Does

In Indian Railways operations, scheduling track maintenance (civil, track, overhead catenary OHE, signalling) requires **Traffic Possessions / Maintenance Blocks**. 

**Layer 3 Optimization Engine** is the mathematical decision core of RailSync. It accepts:
1. Scored maintenance tasks from upstream modules (Layer 1 failure forecasts & Layer 2 department scoring).
2. Available candidate track possession block windows with train traffic conflict data.

It formulates an exact **Constraint Programming (CP-SAT)** model to produce an optimal, conflict-free maintenance schedule that:
- **Strictly guarantees zero passenger train disruptions** (HARD constraint).
- **Enforces track exclusivity** (only 1 maintenance task per track segment per block).
- **Prioritizes high-risk critical tasks** ($\text{risk\_30d} > 0.70$ and $\text{CRITICAL/HIGH}$) into their **next feasible window** (HARD constraint).
- **Allows freight conflicts as a soft penalty** to maintain freight throughput without blocking critical track work.
- **Minimizes active blocks and unused capacity** to maximize rail asset availability.
- **Supports Multi-Horizon Planning** (7-day Weekly tactical vs 30-day Monthly strategic plans).
- **Supports 3 Policy Presets & Pareto Frontier** (Safety-First, Balanced, Throughput-First).
- **Evaluates Scenario Robustness** across $N=50$ Monte Carlo failure-time simulations sampled from Layer 1 survival curves.
- **Pre-computes Plan B Contingency Repository** for Top-5 high-impact disruption scenarios.
- **Provides Fast Re-Optimization Endpoint (<5s guaranteed)** returning revised plans with explainable diffs ("what changed" and "why").

---

## 🔌 2. How Teammates Can Call This Module

Teammates integrating this engine into APIs, backends, or pipelines only need to call simple Python functions with standard Python dictionaries or typed dataclasses.

### Primary Public Functions

```python
from Optimization import (
    optimize_schedule,
    generate_weekly_plan,
    generate_monthly_plan,
    compute_pareto_frontier,
    evaluate_scenario_robustness,
    generate_plan_b_contingencies,
    reoptimize_fast,
)

# 1. Main Optimization Call
result = optimize_schedule(tasks=tasks_data, blocks=blocks_data)

# 2. Multi-Horizon Planning (Weekly & Monthly)
weekly_plan = generate_weekly_plan(tasks=tasks_data, blocks=blocks_data)
monthly_plan = generate_monthly_plan(tasks=tasks_data, blocks=blocks_data)

# 3. 3 Policy Presets & Pareto Frontier Analysis
pareto_res = compute_pareto_frontier(tasks=tasks_data, blocks=blocks_data)

# 4. Scenario Robustness Evaluation (N=50 Layer 1 Survival Curves)
robustness_res = evaluate_scenario_robustness(tasks=tasks_data, blocks=blocks_data, num_scenarios=50)

# 5. Plan B Contingency Repository (Top-5 Precomputed Fallback Plans)
plan_b_repo = generate_plan_b_contingencies(tasks=tasks_data, blocks=blocks_data)
contingency = plan_b_repo.get_plan("SCN-01-RAIL-FRACTURE")

# 6. Fast Re-Optimization Endpoint (<5 seconds guaranteed with explainable diffs)
fast_res = reoptimize_fast(tasks=tasks_data, blocks=blocks_data, disruption=disruption_data)
```


---

## 📥 3. Input Data Format

You can pass standard Python dictionaries / JSON arrays for `tasks` and `blocks`:

### Maintenance Tasks Input (`tasks`)
| Field | Type | Description |
| :--- | :--- | :--- |
| `task_id` | `str` | Unique task ID (e.g. `"TASK-101"`). |
| `segment` | `str` | Track segment ID (e.g. `"NDLS-GZB-UP"`). |
| `claimed_criticality` | `str` | `"CRITICAL"`, `"HIGH"`, `"MEDIUM"`, or `"LOW"`. |
| `min_duration_hrs` | `float` | Minimum required continuous block duration in hours (e.g. `3.0`). |
| `risk_30d` | `float` | 30-day failure risk score between `0.0` and `1.0`. |
| `preferred_window` | `str` (optional) | Preferred block ID (e.g. `"BLK-01"` or `None`). |
| `description` | `str` (optional) | Human-readable maintenance description. |

### Block Windows Input (`blocks`)
| Field | Type | Description |
| :--- | :--- | :--- |
| `block_id` | `str` | Unique block identifier (e.g. `"BLK-01"`). |
| `duration_hrs` | `float` | Continuous available block duration in hours (e.g. `4.0`). |
| `window_index` | `int` | Chronological order index (`0` = earliest next window, `1` = subsequent). |
| `start_time` | `str` (optional) | Start timestamp (e.g. `"2026-09-11 01:00"`). |
| `end_time` | `str` (optional) | End timestamp (e.g. `"2026-09-11 05:00"`). |
| `passenger_conflicts`| `dict` | Segment -> count of passenger trains impacted (if $>0$, HARD conflict). |
| `freight_conflicts` | `dict` | Segment -> count of freight trains delayed (incurs soft penalty). |
| `allowed_segments` | `list` (optional)| Optional restriction list of segments permitted in this block. |

---

## 📤 4. Output Data Format

Calling `result.to_dict()` produces a clean, JSON-serializable dictionary:

```json
{
  "solver_status": "OPTIMAL",
  "objective_score": 21100.0,
  "runtime": 0.0252,
  "total_tasks": 8,
  "scheduled_tasks_count": 8,
  "unassigned_tasks_count": 0,
  "active_blocks": 3,
  "freight_conflicts": 7,
  "scheduled_tasks": [
    {
      "task_id": "TSK-001",
      "assigned_block": "BLK-01",
      "segment": "NDLS-GZB-UP",
      "duration_hrs": 3.0,
      "claimed_criticality": "CRITICAL",
      "risk_30d": 0.88,
      "is_high_risk_critical": true,
      "window_index": 0,
      "freight_conflict_count": 1,
      "freight_penalty_score": 250.0,
      "status": "SCHEDULED",
      "remarks": "Assigned to BLK-01 (Window #0) - High-risk safety critical task scheduled in next feasible window (#0) - Soft penalty applied for 1 freight delay(s)"
    }
  ],
  "unassigned_tasks": [
    {
      "task_id": "TSK-IMPOSSIBLE",
      "assigned_block": null,
      "segment": "SEC-HEAVY",
      "duration_hrs": 5.0,
      "status": "UNASSIGNED",
      "remarks": "Task duration (5.0h) exceeds all available block windows"
    }
  ],
  "block_summaries": [
    {
      "block_id": "BLK-01",
      "window_index": 0,
      "duration_hrs": 4.0,
      "is_utilized": true,
      "assigned_tasks": ["TSK-001", "TSK-002", "TSK-003", "TSK-005", "TSK-008"],
      "segments_blocked": ["NDLS-GZB-UP", "GZB-ALJN-DN", "ALJN-TDL-UP", "ETW-CNB-UP", "TDL-ETW-DN"],
      "total_freight_delays": 5,
      "utilized_hours_max": 4.0,
      "unused_capacity_hrs": 0.0
    }
  ]
}
```

---

## 🚦 5. Solver Status Meanings

| Solver Status | Meaning | Action Needed |
| :--- | :--- | :--- |
| **`OPTIMAL`** | Mathematically proven best feasible schedule found respecting all hard constraints and minimizing objective cost. | Use schedule directly. |
| **`FEASIBLE`** | A valid, conflict-free schedule was found within the solver timeout limit (good quality, though not mathematically proven global minimum). | Use schedule directly. |
| **`INFEASIBLE`** | Mathematical contradiction in hard constraints (e.g. invalid task models). | Check input constraint parameters. |
| **`MODEL_INVALID`** | Input data structure error (e.g. malformed variables). | Check task/block data types. |

---

## ⚖️ 6. Hard vs Soft Constraints

```
┌────────────────────────────────────────────────────────────────────────┐
│                        HARD CONSTRAINTS (Strict)                       │
├────────────────────────────────────────────────────────────────────────┤
│ 1. At most one block assignment per task.                              │
│ 2. One task per segment per block (Different segments CAN share).     │
│ 3. Task duration <= Block duration.                                    │
│ 4. Passenger Train Conflict = 0 (STRICT PROHIBITION).                  │
│ 5. High-Risk Critical Tasks (risk > 0.70 & CRITICAL/HIGH) MUST be      │
│    scheduled in their next feasible window.                            │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        SOFT CONSTRAINTS (Penalties)                    │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Freight Train Delays: Incurs penalty per freight train delayed.     │
│ 2. Unassigned Tasks: Heavy penalty if routine tasks cannot be placed.  │
│ 3. Window Delay: Urgency penalty pushing tasks to earlier windows.     │
│ 4. Block Activation: Penalty per block to promote bundling.            │
│ 5. Unused Capacity: Penalty for idle block hours.                      │
│ 6. Department Preference: Bonus reward for honoring preferred window. │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ 7. Configurable Weights (`config.py`)

All policy thresholds and objective weights are centralized in [config.py](file:///c:/Users/LENOVO/OneDrive/Desktop/RailSync/optimization/config.py):

| Parameter | Current Default | Purpose |
| :--- | :--- | :--- |
| `HIGH_RISK_THRESHOLD` | `0.70` | Cutoff probability for safety-critical tasks requiring immediate window. |
| `ENFORCE_STRICT_HIGH_RISK_NEXT_WINDOW` | `True` | Enforces hard constraint for high-risk critical next feasible window. |
| `WEIGHT_UNASSIGNED_TASK_BASE_PENALTY` | `10000` | Penalty for leaving a maintenance task unscheduled. |
| `WEIGHT_UNASSIGNED_HIGH_RISK_PENALTY` | `50000` | Heavy penalty if high-risk tasks remain unscheduled. |
| `WEIGHT_WINDOW_DELAY_PENALTY` | `500` | Urgency multiplier pushing tasks to earlier windows. |
| `WEIGHT_FREIGHT_CONFLICT_PENALTY` | `250` | Soft penalty per freight train delayed during block possession. |
| `WEIGHT_BLOCK_ACTIVATION_PENALTY` | `1000` | Penalty per block opened to incentivize task bundling/consolidation. |
| `WEIGHT_UNUSED_BLOCK_CAPACITY_PENALTY` | `100` | Penalty for unused block capacity hours to preserve network capacity. |
| `WEIGHT_PREFERRED_WINDOW_BONUS` | `300` | Bonus reward for honoring department requested windows. |

---

## 💡 8. Important Assumptions

1. **Integer Arithmetic**: Google OR-Tools CP-SAT operates on integer linear formulations. Floating-point hours are scaled internally by `SCALE_FACTOR = 100` (e.g. `2.5h` -> `250 units`) preserving exact precision without rounding error.
2. **Passenger Priority**: Passenger train traffic cannot be cancelled or delayed for scheduled maintenance blocks. If a passenger train passes on segment $s$ during block $b$, segment $s$ cannot be possessed in block $b$.
3. **Freight Elasticity**: Freight trains can be regulated, looped, or delayed during block possessions, incurring operational penalties.
4. **Segment Exclusivity**: Multiple maintenance teams working on the *exact same physical track segment* simultaneously poses safety and clearance hazards; however, teams working on *different segments* can safely utilize the same system block window.

---

## 💻 9. Minimal Integration Example

Run the included example script:
```bash
python optimization/example_usage.py
```

### Python Code Snippet:
```python
from optimization import optimize_schedule

# 1. Tasks input
tasks = [
    {
        "task_id": "TASK-101",
        "segment": "NDLS-GZB-UP",
        "claimed_criticality": "CRITICAL",
        "min_duration_hrs": 3.0,
        "risk_30d": 0.88,
        "preferred_window": "BLK-01"
    }
]

# 2. Block windows input
blocks = [
    {
        "block_id": "BLK-01",
        "duration_hrs": 4.0,
        "window_index": 0,
        "passenger_conflicts": {"NDLS-GZB-UP": 0},
        "freight_conflicts": {"NDLS-GZB-UP": 1}
    }
]

# 3. Call optimizer
result = optimize_schedule(tasks, blocks)

# 4. Access output dictionary
output_dict = result.to_dict()
print("Status:", output_dict["solver_status"])
print("Scheduled Tasks:", output_dict["scheduled_tasks"])
```

---

## 🚀 10. How to Run Commands

### Run All 9 Operational Unit Tests:
```bash
python optimization/test_optimizer.py
```

### Run Main Optimizer (Synthetic Delhi–Kanpur Corridor Dataset):
```bash
python optimization/optimizer.py
```

### Run What-If Disruption Demo:
```bash
python optimization/what_if.py
```

### Run Integration Demo:
```bash
python optimization/example_usage.py
```
