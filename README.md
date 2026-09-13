---
title: RailSync 2.0 National Railway Command Center
emoji: 🚆
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🚆 RailSync 2.0

### AI-Powered Automatic Block Planning for Indian Railways

RailSync 2.0 is a **Smart India Hackathon prototype** that uses **Artificial Intelligence + Operations Research** to automatically coordinate railway maintenance blocks across Track, Traction/OHE, and Signal & Telecommunication departments.

The system combines **failure-risk forecasting, evidence-based department negotiation, CP-SAT optimization, disruption re-planning, and execution feedback** to maximize asset availability while minimizing disruption to train operations.

---

## 🎯 Problem

Railway maintenance activities are planned independently by different departments. Maintenance requests, asset conditions, and corridor availability are distributed across systems such as TMS, SMMS, TDMS, BDMS and COA.

This decentralized planning process can result in:

- Poor coordination between departments
- Conflicting maintenance requests
- Inefficient block utilization
- Excessive asset downtime
- Difficulty responding to unexpected disruptions

### 💡 Our Solution

RailSync creates a unified AI-powered planning pipeline:

```text
Asset & Maintenance Data
          ↓
   Failure Forecasting
          ↓
 Department Negotiation
          ↓
   CP-SAT Optimization
          ↓
 Weekly / Monthly Plan
          ↓
 Disruption Re-planning
          ↓
    Feedback & Learning
```

---

# 🏗️ System Architecture

```text
┌─────────────────────────────────┐
│     LAYER 0 — DATA GENERATION   │
│                                 │
│ Assets • Defects • Maintenance  │
│ Timetable • Block Availability  │
└───────────────┬─────────────────┘
                ↓
┌─────────────────────────────────┐
│   LAYER 1 — FAILURE FORECASTING │
│                                 │
│ XGBoost Survival Model          │
│ Weibull AFT Baseline            │
│ Risk • Downtime • Confidence    │
└───────────────┬─────────────────┘
                ↓
┌─────────────────────────────────┐
│    LAYER 2 — NEGOTIATION        │
│                                 │
│ Evidence Score                  │
│ Criticality Validation          │
│ Priority & Task Consolidation   │
└───────────────┬─────────────────┘
                ↓
┌─────────────────────────────────┐
│    LAYER 3 — OPTIMIZATION       │
│                                 │
│ Google OR-Tools CP-SAT          │
│ Multi-objective Planning        │
│ Robustness • Plan B             │
└───────────────┬─────────────────┘
                ↓
┌─────────────────────────────────┐
│      LAYER 4 — FEEDBACK         │
│                                 │
│ Planned vs Actual               │
│ Duration Recalibration          │
└───────────────┬─────────────────┘
                ↓
        React Dashboard
```

---

# ✨ Key Features

## 🤖 AI Failure Forecasting

- Discrete-time survival modelling
- XGBoost-based failure-risk prediction
- Weibull AFT interpretable baseline
- 30-day failure probability
- Expected downtime prediction
- Preventive block duration prediction
- Confidence score
- SHAP-style feature explanations

Example output:

```text
Segment: TRK-D01-023

Risk (30 days):          0.78
Expected Downtime:       3.4 days
Preventive Block:        2.5 hrs
Confidence:              High
```

---

## 🤝 Department Negotiation

Departments submit maintenance requests containing:

```text
Task ID
Segment
Department
Claimed Criticality
Minimum Duration
Preferred Window
```

RailSync then:

1. Validates claimed criticality against AI-generated evidence
2. Calculates an evidence score
3. Flags potentially inflated criticality claims
4. Calculates task priority
5. Consolidates compatible maintenance tasks
6. Produces a scored task pool for optimization

Example:

```text
Claimed Criticality: 5
Evidence Score:      0.24

→ INFLATED CLAIM FLAGGED
```

---

# 🧮 CP-SAT Optimization

RailSync uses **Google OR-Tools CP-SAT** to generate operationally feasible maintenance schedules.

### Constraints

- Only one task per segment per block window
- Task duration must fit within the available block
- Passenger train paths are hard constraints
- Freight conflicts are handled through penalties
- High-risk critical tasks receive priority scheduling

### Objectives

The optimizer balances:

```text
Asset Availability
        +
Risk Reduction
        +
Criticality
        +
Urgency
        +
Block Consolidation
        -
Operational Disruption
```

---

# 🛡️ Robust Planning & Plan B

RailSync does not rely only on one deterministic future.

It samples failure-time scenarios from Layer 1 survival curves and evaluates the robustness of the generated plan.

```text
                 Current Plan
                      │
          ┌───────────┼───────────┐
          ↓           ↓           ↓
      Scenario 1  Scenario 2  Scenario 3
          │           │           │
          ↓           ↓           ↓
        Plan B      Plan B      Plan B
```

The system reports a **robustness percentage** and stores fallback plans for major disruption scenarios.

---

# ⚡ What-if Re-optimization

RailSync can inject unexpected operational events.

Example:

```text
Track defect detected
Segment: TRK-D01-023
Time: 11:30
```

The optimizer generates a revised plan and explains:

```text
✓ Task A moved
✓ Task B consolidated
✓ Task C delayed
✓ New emergency task inserted

Reason:
High-risk defect + unavailable original block
```

Target re-optimization time:

```text
< 5 seconds
```

---

# 📈 Feedback Loop

Every executed maintenance block can be logged with:

```text
Planned Duration
Actual Duration
Overrun Cause
```

This allows RailSync to track prediction performance over time.

```text
Planned Duration
        ↓
Actual Duration
        ↓
Prediction Error
        ↓
Monthly Recalibration
        ↓
Improved Duration Prediction
```

---

# 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3.11 |
| Data Processing | pandas, NumPy |
| Machine Learning | XGBoost, scikit-learn |
| Survival Analysis | lifelines |
| Optimization | Google OR-Tools CP-SAT |
| Backend | FastAPI |
| Database | SQLite |
| Frontend | React.js |
| Visualization | Recharts / Gantt |
| Development | VS Code + GitHub |
| ML Experiments | Google Colab |

---

# 📁 Project Structure

```text
RailSync/
│
├── Backend/
│   └── FastAPI backend
│
├── Frontend/
│   └── React dashboard
│
├── Optimization/
│   └── CP-SAT optimization engine
│
├── Railsync_2.0_Layer_0_FINAL/
│   └── Layer 0 synthetic data
│
├── Railsync_2.0_Layer_1_Colab_Package/
│   └── Layer 1 training package
│
├── Railsync_Layer_1_Complete/
│   └── Layer 1 forecasting
│
├── Railsync_Layer_2_Outputs/
│   └── Layer 2 negotiation outputs
│
├── demo_sih_pipeline.py
│   └── End-to-end SIH pipeline
│
├── RULES.md
│   └── Synthetic data causal rules
│
├── DEMO_SCRIPT.md
│   └── SIH demonstration script
│
└── README.md
```

---

# 🔄 End-to-End Data Flow

```text
                    ┌───────────────┐
                    │  Railway Data │
                    └───────┬───────┘
                            ↓
                 ┌────────────────────┐
                 │ Layer 0            │
                 │ Synthetic Dataset  │
                 └─────────┬──────────┘
                           ↓
                 ┌────────────────────┐
                 │ Layer 1            │
                 │ Risk Forecasting   │
                 └─────────┬──────────┘
                           ↓
                 ┌────────────────────┐
                 │ Layer 2            │
                 │ Negotiation        │
                 └─────────┬──────────┘
                           ↓
                 ┌────────────────────┐
                 │ Layer 3            │
                 │ CP-SAT Optimization│
                 └─────────┬──────────┘
                           ↓
                 ┌────────────────────┐
                 │ Weekly / Monthly   │
                 │ Maintenance Plan   │
                 └─────────┬──────────┘
                           ↓
                 ┌────────────────────┐
                 │ React Dashboard    │
                 └─────────┬──────────┘
                           ↓
                 ┌────────────────────┐
                 │ Layer 4            │
                 │ Feedback Loop      │
                 └────────────────────┘
```

---

# 🧠 Layer 1 — Model Evaluation

RailSync uses a **timeline-based evaluation split** rather than randomly shuffling data.

```text
Training Data
Months 1 ─────────────── 18

Testing Data
Months 19 ─────── 24
```

Evaluation metrics include:

- C-index
- Brier Score
- Calibration Curve
- Top-20 Precision
- Base-rate comparison

---

# 📊 Layer 1 Outputs

For every asset segment:

```text
risk_30d
survival_curve
expected_downtime_days
preventive_block_duration_hrs
confidence
```

These outputs are passed directly into the downstream planning pipeline.

```text
Layer 1 Risk
     ↓
Layer 2 Evidence Score
     ↓
Task Priority
     ↓
Layer 3 Optimization
```

---

# 🖥️ Dashboard

The React dashboard provides:

### 1. 🚦 Corridor Risk Map

Segments are visualized according to their predicted failure risk.

```text
🟢 Low Risk
🟡 Medium Risk
🔴 High Risk
```

### 2. 📅 Schedule View

Gantt-style weekly/monthly maintenance plan.

### 3. ❓ Why? Panel

Shows feature contributions behind a segment's risk prediction.

### 4. 🌪️ What-if Panel

Inject a disruption and view the revised Plan B.

### 5. 🤝 Negotiation View

Compare departmental claims against evidence scores.

### 6. ⚖️ Pareto View

Compare:

```text
Safety-first
Balanced
Throughput-first
```

### 7. 📈 Feedback Trend

Shows predicted-vs-actual duration error over time.

---

# 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/ingest/tasks` | Submit maintenance task |
| GET | `/risk/segments` | Get risk for all segments |
| GET | `/risk/{segment_id}` | Get detailed segment forecast |
| POST | `/negotiate` | Run department negotiation |
| POST | `/optimize` | Generate maintenance plan |
| POST | `/optimize/whatif` | Inject disruption |
| GET | `/plan/current` | Get current plan |
| POST | `/feedback/block` | Log executed block |
| GET | `/feedback/metrics` | Get feedback metrics |

When the backend is running, FastAPI provides interactive API documentation at:

```text
http://localhost:8000/docs
```

---

# 🚀 Getting Started

## Prerequisites

Install:

- Python 3.11
- Node.js
- npm
- Git

---

## 1. Clone the Repository

```bash
git clone <YOUR-REPOSITORY-URL>
cd RailSync
```

---

## 2. Create Python Virtual Environment

### macOS / Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

---

## 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Install Frontend Dependencies

```bash
cd Frontend
npm install
cd ..
```

---

## 5. Run the SIH Pipeline

```bash
python demo_sih_pipeline.py
```

The intended end-to-end workflow is:

```text
Generate Data
     ↓
Train / Load Models
     ↓
Run Negotiation
     ↓
Run Optimization
     ↓
Start Backend
     ↓
Start Dashboard
```

---

# 🎬 SIH Demo Flow

The recommended 8-minute demonstration:

```text
01. Problem & Architecture
          ↓
02. Failure Forecast
          ↓
03. "Why?" Explanation
          ↓
04. Department Negotiation
          ↓
05. Generate Optimized Plan
          ↓
06. Inject Disruption
          ↓
07. Plan B Activation
          ↓
08. Pareto Comparison
          ↓
09. Feedback Loop
```

Detailed demo instructions are available in:

```text
DEMO_SCRIPT.md
```

---

# 🧪 Evaluation Checklist

Before the SIH presentation:

```text
☐ Synthetic data generator works
☐ RULES.md documents causal assumptions
☐ Layer 1 timeline split is implemented
☐ C-index is calculated
☐ Brier score is calculated
☐ Calibration is available
☐ Top-20 precision is calculated
☐ Risk outputs reach the optimizer
☐ Department negotiation works
☐ Inflated claims are detected
☐ Passenger conflicts are prevented
☐ Freight penalties work
☐ Three policy presets produce different plans
☐ Robustness score is generated
☐ Plan B is generated
☐ What-if re-optimization works
☐ Risk explanation is visible
☐ Feedback metrics are displayed
☐ End-to-end demo runs without manual debugging
```

---

# 🧩 Key Differentiators

RailSync is not just a machine-learning model and not just a scheduling algorithm.

Its core innovation is the integration of **AI-based asset risk with operational railway block planning**.

```text
                 AI Risk
                    ↓
             Evidence-based
              Negotiation
                    ↓
             Task Prioritization
                    ↓
              CP-SAT Planning
                    ↓
             Robustness Testing
                    ↓
                 Plan B
                    ↓
             Execution Feedback
                    ↓
              Model Learning
```

### RailSync enables:

- **Risk-aware maintenance scheduling**
- **Evidence-based prioritization**
- **Cross-department block consolidation**
- **Operationally constrained planning**
- **Scenario-based robustness**
- **Fast disruption recovery**
- **Continuous feedback and recalibration**

---

# 📚 Documentation

| File | Purpose |
|---|---|
| `README.md` | Project overview and setup |
| `RULES.md` | Synthetic data generation rules |
| `DEMO_SCRIPT.md` | SIH presentation sequence |

---

# 👥 Team Responsibilities

Suggested ownership:

| Role | Responsibility |
|---|---|
| Data / Python | Synthetic data & data pipeline |
| ML | Failure forecasting |
| Optimization | CP-SAT, robustness & Plan B |
| Backend | FastAPI & integration |
| Frontend | React dashboard |
| Presentation | SIH demo & pitch |

---

# 🚆 RailSync 2.0

### Predict Risk → Negotiate Fairly → Optimize Blocks → Handle Disruption → Learn from Execution

**Smart India Hackathon Project**
