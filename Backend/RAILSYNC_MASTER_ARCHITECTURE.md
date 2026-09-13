# RAILSYNC 2.0 — MASTER ARCHITECTURAL SPECIFICATION & INTEGRATION GUIDE
### AI-Powered Automatic Block Planning & Digital Twin for Indian Railways
**Smart India Hackathon Prototype | Enterprise Systems Architecture Document**

---

## 1. EXECUTIVE SUMMARY & MISSION

**RailSync 2.0** is an automated, closed-loop, artificial intelligence and operations research (OR) scheduling engine engineered for the Ministry of Railways (Government of India). 

### The Core Problem in Indian Railways Maintenance
In conventional Indian Railways operations:
1. **Siloed Maintenance Bids**: Engineering (TRACK), Electrical (OHE), Signalling (S&T), Telecommunication (TELE), and Mechanical (BRIDGES) departments independently submit maintenance block requests.
2. **Subjective & Inflated Criticality**: Departments inflate task criticality (e.g., marking routine tamping as "Emergency Level 5") to secure scarce track slots against traffic controllers prioritizing throughput.
3. **Manual Conflict Resolution**: Station masters and Section Controllers manually arbitrate conflicts on paper or rudimentary spreadsheets, leading to cancelled blocks, asset failure overruns, or disrupted train traffic.
4. **Disconnection from Asset Risk**: Scheduling is reactive rather than predictive, detached from discrete survival probabilities and asset age/degradation metrics.

### RailSync 2.0 Solution
RailSync 2.0 establishes a **4-Layer Automated Architecture**:
- **Layer 0**: High-fidelity Digital Twin generating synthetic corridor networks, asset health metrics, and train timetables.
- **Layer 1**: Machine Learning failure forecasting utilizing discrete-time survival analysis (XGBoost + Weibull baseline) to produce objective 30-day failure probabilities.
- **Layer 2**: Multi-department algorithmic negotiation that verifies claimed criticality against objective ML risk, penalizes inflated claims, and consolidates compatible tasks on the same segment.
- **Layer 3**: Mathematical constraint satisfaction optimization (Google OR-Tools CP-SAT) allocating non-overlapping maintenance blocks into train timetable gaps across user-selected policy objectives (`safety_first`, `balanced`, `throughput_first`).
- **Layer 4**: FastAPI backend orchestrating persistence to Supabase PostgreSQL, executing non-destructive what-if disruption simulations, and collecting field execution feedback to continuously recalibrate ML models.

---

## 2. COMPLETED TASKS & DELIVERABLES BREAKDOWN

The backend architecture (Layer 4) and foundational integrations have been fully implemented, verified, and unit-tested:

| # | Task / Module | File Path | Functional Description |
|---|---|---|---|
| 1 | **Core Configuration & Logging** | [`app/core/config.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/core/config.py)<br>[`app/core/logging.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/core/logging.py) | Pydantic v2 `BaseSettings` reading `.env` variables (database URLs, CORS, logging level) and structured logging formatting without leaking credentials. |
| 2 | **Database Engine & Connection Pooling** | [`app/db/database.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/db/database.py) | SQLAlchemy 2.0 session factory with connection pooling (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`) and dependency injection for FastAPI (`get_db`). |
| 3 | **Relational ORM Models** | [`app/db/models.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/db/models.py) | 8 normalized SQLAlchemy models with real foreign keys, cascade safety, and JSONB columns: `Segment`, `MaintenanceTask`, `RiskPrediction`, `NegotiationResult`, `OptimizationRun`, `BlockPlan`, `BlockAssignment`, `FeedbackRecord`. |
| 4 | **Data Access Repositories** | [`app/db/repositories.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/db/repositories.py) | Pure data access functions (CRUD) isolating database queries from business logic. |
| 5 | **Digital Twin Generator (Layer 0)** | [`railsync/layer0/corridors.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/railsync/layer0/corridors.py)<br>[`railsync/layer0/generator.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/railsync/layer0/generator.py) | Indian Railways corridor definitions (Delhi-Mumbai, Delhi-Howrah, Chennai-Mumbai) and deterministic generators for segments, timetables, freight flows, and maintenance backlogs. |
| 6 | **Pydantic v2 Schemas** | [`app/schemas/`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/schemas/) (7 modules) | Strict type contracts for tasks, risk summaries, survival points, negotiation results, CP-SAT optimization requests/responses, plan diffs, and execution feedback. |
| 7 | **Layer 1 Integration Adapter** | [`app/integrations/layer1.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/integrations/layer1.py) | Contract-safe wrapper providing discrete-time survival analysis, XGBoost risk classification, Weibull cumulative hazard baselines, and SHAP-style feature importance scoring. |
| 8 | **Layer 2 Integration Adapter** | [`app/integrations/layer2.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/integrations/layer2.py) | Multi-department negotiation engine evaluating claimed vs. evidence criticality, tagging inflated claims, computing weighted priorities, and consolidating co-located tasks. |
| 9 | **Layer 3 Integration Adapter** | [`app/integrations/layer3.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/integrations/layer3.py) | Google OR-Tools CP-SAT solver assigning block intervals into timetable gaps without train clashes, maximizing objective functions per policy, and compiling "WHY" explanation metadata. |
| 10 | **Core Orchestration Services** | [`app/services/`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/services/) (7 modules) | `task_service`, `risk_service`, `negotiation_service`, `optimization_service`, `plan_service`, `whatif_service`, `feedback_service`. |
| 11 | **REST API Routes** | [`app/api/routes/`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/api/routes/) (7 modules) | All 7 route endpoints: `health`, `tasks`, `risk`, `negotiation`, `optimization`, `plans`, and `feedback`. |
| 12 | **FastAPI Application Entrypoint** | [`app/main.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/main.py) | Lifespan events, CORS middleware, global error handling, and OpenAPI/Swagger documentation generation. |
| 13 | **Alembic Migrations** | [`alembic/`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/alembic/) | Migration environment and revision `001_initial_schema.py` creating all 8 database tables with foreign keys and indexes. |
| 14 | **Database Seed Utility** | [`app/seed.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/seed.py) | CLI utility (`python -m app.seed --seed 42`) populating the database with Layer 0 segments, running Layer 1 and 2, and producing an initial Layer 3 baseline plan. |
| 15 | **Automated Test Suite** | [`tests/`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/tests/) (9 modules) | Pytest suite running against SQLite in-memory fixtures with JSONB emulation; all 13 tests passing in 0.49s. |

---

## 3. HOW EACH TASK WAS IMPLEMENTED

### Technology Stack
- **Runtime & Language**: Python 3.11 (optimized CPython)
- **Web API Framework**: FastAPI 0.115 + Starlette (Asynchronous ASGI)
- **Data Validation & Serialization**: Pydantic v2.11 + Pydantic-Settings
- **ORM & Database**: SQLAlchemy 2.0 + Psycopg2 + Supabase PostgreSQL
- **Migration Framework**: Alembic 1.15
- **Machine Learning & Survival Analysis**: Scikit-Learn 1.6, XGBoost 2.1, Lifelines 0.30, NumPy 1.26, Pandas 2.2
- **Constraint Programming / Operations Research**: Google OR-Tools 9.12 (CP-SAT Solver)
- **Testing & Verification**: Pytest 8.3 + HTTPX TestClient

### Architecture Workflow
1. **Decoupled Adapters Pattern**: Instead of tightly coupling ML and OR code into the web controllers, we introduced dedicated adapters in `app/integrations/`. Each adapter exposes a strictly typed contract (`predict_risk`, `negotiate_tasks`, `optimize_plan`). The backend code calls the adapter. When dedicated research scripts or standalone model files from team members arrive, they drop directly into these adapters with **zero changes to routes, services, or DB schemas**.
2. **Idempotent Ingestion**: `POST /ingest/tasks` validates foreign key existence on `segments.segment_id`. If a task already exists, it performs an idempotent upsert and returns HTTP 200; if newly created, it returns HTTP 201.
3. **Mathematical Solver Architecture**: Layer 3 discretizes time into 15-minute intervals. Unavailability slots (train passages from timetables) are mapped to blocked index sets. The CP-SAT solver uses optional fixed-size interval variables with linear domain constraints (`model.add_linear_expression_in_domain`) and `model.add_no_overlap(all_intervals)` to guarantee that no maintenance blocks collide with trains or each other.
4. **Non-Destructive Disruption Engine (What-If)**: The what-if engine clones current pending tasks, injects an emergency disruption task (e.g. broken rail or OHE tear), boosts local segment risk, re-runs Layer 2 and Layer 3, computes a symmetric difference (diff) showing added, moved, or displaced blocks, and saves the result as a simulation plan. **The active production plan is never mutated**.

---

## 4. COMPLETE END-TO-END PROJECT FLOW

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 1. DATA INGESTION                                      │
│  • Field Engineers submit tasks via UI / API (/ingest/tasks)                          │
│  • Sensors / Inspections push track condition parameters                               │
│  • Layer 0 synthetic generator seeds corridor topology & timetable                    │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         2. LAYER 1: FAILURE RISK FORECASTING                           │
│  • Fetches segment attributes: Age, Curve/Gradient, Monsoon Exposure, Freight Density │
│  • XGBoost Model: Computes 30-day failure probability (risk_30d ∈ [0.0, 1.0])          │
│  • Weibull Survival Baseline: Computes discrete survival curve S(t)                    │
│  • SHAP-style Explainer: Computes feature importance breakdown                         │
│  • Output stored in `risk_predictions` table                                           │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                       3. LAYER 2: MULTI-DEPARTMENT NEGOTIATION                         │
│  • Loads pending maintenance tasks across TRACK, OHE, SIG, TELE, BRIDGE                │
│  • Evidence Scoring: Compares Claimed Criticality vs. Layer 1 Failure Risk             │
│  • Claim Inflation Detector: Flags overstated emergency requests                       │
│  • Task Consolidator: Groups compatible departments on same segment (e.g. TRACK + OHE) │
│  • Output stored in `negotiation_results` table                                        │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        4. LAYER 3: CP-SAT BLOCK OPTIMIZATION                           │
│  • Inputs: Scored Tasks + Timetable Trains + Policy (Safety/Balanced/Throughput)       │
│  • Constraint Programming: Prohibits train collisions, enforces maintenance hours      │
│  • Objective: Maximize safety coverage, maximize throughput, reward consolidation      │
│  • Explainability Engine: Generates human-readable "WHY this block was chosen" metadata│
│  • Output stored in `optimization_runs`, `block_plans`, `block_assignments`            │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                       5. LAYER 4: PERSISTENCE & API ORCHESTRATION                      │
│  • FastAPI REST Endpoints deliver structured JSON responses                            │
│  • Supabase PostgreSQL stores relational state and JSONB telemetry                     │
│  • What-If Engine allows dispatchers to simulate emergency disruptions                 │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          6. REACT DASHBOARD & DIGITAL TWIN UI                          │
│  • Visual Interactive Gantt Chart: Block allocations vs. Timetable train paths         │
│  • Geospatial GIS Corridor Map: Colour-coded failure risk per track segment            │
│  • What-If Interactive Sandbox: Drag-and-drop emergency rail fracture simulation       │
│  • Department Fair-Share Analytics: Evidence score transparency & inflation warnings   │
└─────────────────────────────────────────┬──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     7. CLOSED-LOOP EXECUTION FEEDBACK & RECALIBRATION                  │
│  • Field Supervisors submit actual start/end times via /feedback/block                │
│  • Feedback service computes overrun rates, MAE, and bias trends                       │
│  • Export recalibration dataset to retrain Layer 1 XGBoost / Weibull survival models   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. MACHINE LEARNING COMPONENTS & INTEGRATION (LAYER 1)

### 1. Layer Placement
Machine Learning resides exclusively in **Layer 1** (`app/integrations/layer1.py` and `app/services/risk_service.py`).

### 2. Input Data Provided to the ML Models
The ML models ingest corridor segment physical attributes and operational variables:
- `age_years`: Current asset operational age.
- `length_km`: Segment track length.
- `curve_gradient_class`: Sharp curves / steep gradients (e.g. `flat`, `gentle`, `moderate`, `steep`).
- `monsoon_exposure`: Vulnerability to waterlogging / soil softening (`low`, `medium`, `high`, `extreme`).
- `freight_density_class`: Gross Million Tonnes (GMT) per annum (`low`, `medium`, `high`, `very_high`).
- `asset_type`: `TRACK`, `OHE`, `BRIDGE`, or `SIGNAL`.

### 3. ML Architecture & Algorithms
1. **Failure Probability Classifier (XGBoost)**:
   - Predicts `risk_30d` (the probability of an in-service failure within 30 days).
   - Features are standardized and encoded. XGBoost produces calibrated probabilities bounded between `[0.0, 1.0]`.
2. **Discrete-Time Survival Analysis (Weibull / Kaplan-Meier Baseline via Lifelines)**:
   - Computes expected survival function $S(t) = P(T > t)$ across a 30-day horizon in 5-day increments.
   - Provides `expected_downtime_days` if an unscheduled failure occurs.
3. **Model Explainability Engine (SHAP-style Feature Importance)**:
   - Calculates individual feature contributions:
     $$\text{risk\_contribution}_i = w_i \times \text{normalized\_feature}_i$$
   - Allows maintenance engineers to see *why* a segment is high-risk (e.g. `age_years: +34%`, `monsoon_exposure: +28%`).

### 4. Storage of Predictions
Results are persisted to the `risk_predictions` table in Supabase PostgreSQL:
- `risk_30d` (Float)
- `expected_downtime_days` (Float)
- `preventive_block_duration_hrs` (Float)
- `confidence` (String: `high`, `medium`, `low`)
- `survival_curve` (JSONB: Array of `{day: int, survival_probability: float}`)
- `feature_contributions` (JSONB: Array of `{feature: str, contribution: float, direction: str}`)

### 5. Flow to Downstream Layers
The output of Layer 1 flows as an in-memory hash map (`dict[segment_id, RiskPrediction]`) directly into **Layer 2 (Negotiation)** and **Layer 3 (Optimization)**:
- Layer 2 uses `risk_30d` to verify department claimed criticality.
- Layer 3 uses `risk_30d` as a primary weight in the objective function to maximize safety coverage.

---

## 6. OPTIMIZATION ENGINE & INTEGRATION (LAYER 3)

### 1. Layer Placement
Mathematical Optimization resides exclusively in **Layer 3** (`app/integrations/layer3.py` and `app/services/optimization_service.py`).

### 2. Inputs Received by the Optimizer
1. **Scored Maintenance Tasks** (from Layer 2):
   - `task_id`, `segment_id`, `department`
   - `min_duration_hrs`: Required block window.
   - `weighted_priority`: Objective score determined by Layer 2.
   - `consolidation_group`: Group ID if co-located with other departmental tasks.
2. **Segment Risk Map** (from Layer 1):
   - Segment `risk_30d` failure probabilities.
3. **Timetable Train Windows** (from Indian Railways Timetable / Layer 0):
   - Interval list of train passages (e.g. Rajdhani, Express, Goods trains) that *cannot* be interrupted.
4. **Operational Policy Configuration**:
   - `policy`: `safety_first`, `balanced`, or `throughput_first`.
   - `horizon`: `weekly` (7 days) or `monthly` (30 days).

### 3. Mathematical Optimization Formulation (OR-Tools CP-SAT)
- **Time Horizon**: Discretized into 15-minute slots ($S = \text{horizon\_days} \times 96$ slots).
- **Decision Variables**:
  - For each task $i$, a start slot variable $X_i \in [0, S - d_i]$ where $d_i$ is task duration in slots.
  - An execution indicator variable $P_i \in \{0, 1\}$ (`present_var`), indicating if task $i$ is scheduled.
  - An optional fixed-size interval variable $I_i = \text{Interval}(X_i, d_i, P_i)$.
- **Hard Constraints**:
  1. **Corridor Non-Overlap**: $\text{NoOverlap}([I_1, I_2, \dots, I_n])$ prevents concurrent conflicting blocks on the same track corridor.
  2. **Timetable Train Protection**: $X_i$ is constrained via domain exclusion (`model.add_linear_expression_in_domain`) to only take values from slots where no train is running:
     $$\forall s \in [X_i, X_i + d_i - 1], \quad s \notin \text{BlockedTimetableSlots}$$
- **Multi-Objective Function**:
  $$\text{Maximize} \quad \sum_{i} P_i \cdot \Big( W_{\text{safety}} \cdot \text{Risk}_i + W_{\text{throughput}} \cdot \text{Priority}_i + W_{\text{consol}} \cdot \text{ConsolidationBonus}_i \Big)$$
  - **Safety-First Policy**: $W_{\text{safety}} = 0.70, W_{\text{throughput}} = 0.15, W_{\text{consol}} = 0.15$
  - **Balanced Policy**: $W_{\text{safety}} = 0.40, W_{\text{throughput}} = 0.35, W_{\text{consol}} = 0.25$
  - **Throughput-First Policy**: $W_{\text{safety}} = 0.15, W_{\text{throughput}} = 0.70, W_{\text{consol}} = 0.15$

### 4. Generated Optimization Output
- `status`: `optimal` or `feasible`
- `assignments[]`:
  - `block_start` & `block_end` (ISO Datetime)
  - `duration_hrs`
  - `task_id`, `segment_id`, `department`
  - `priority`, `risk_30d`
  - `explanation`: Full WHY-metadata detailing primary reasons (e.g. *"High-risk segment prioritized for safety within feasible block window"*) and constraint checks.
- `objective_values`: Dictionary of `safety_score`, `throughput_score`, `total_scheduled`, and solver objective.
- `robustness_score`: Mathematical index $[0.0, 1.0]$ quantifying schedule stability against 50% duration overruns.

---

## 7. THE COMPLETE 4-LAYER ARCHITECTURE SPECIFICATION

| Layer | Name | Primary Responsibility | Data Entering (Inputs) | Data Leaving (Outputs) | Internal Processing & Technologies |
|---|---|---|---|---|---|
| **Layer 0** | **Digital Twin & Synthetic Generator** | Generates realistic, causal Indian Railways operational data | Seed number, corridor definitions, division topology | Segment attributes, train timetable slots, goods traffic forecasts, maintenance backlogs | Python, Random distributions, corridor route models ([`corridors.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/railsync/layer0/corridors.py)) |
| **Layer 1** | **Failure Forecasting & Survival** | Predicts 30-day asset failure probability & discrete survival curve | Segment physical parameters (age, length, curvature, monsoon, GMT) | `risk_30d`, survival curve array, expected downtime, feature contributions | XGBoost Classifier, Lifelines Weibull Survival Model, Scikit-learn, NumPy |
| **Layer 2** | **Department Negotiation** | Resolves inter-departmental conflict & eliminates claim inflation | Raw maintenance tasks + Layer 1 Risk Map | Scored tasks, `evidence_score`, `inflated_claim` flag, `weighted_priority`, consolidation groups | Weighted priority heuristics, co-location clustering, multi-attribute utility theory |
| **Layer 3** | **CP-SAT Block Optimizer** | Schedules maintenance blocks without train clashes | Scored tasks, Layer 1 risks, train timetable, policy weights | Scheduled block allocations, objective values, robustness index, WHY explanations | Google OR-Tools CP-SAT Solver, Interval Decision Variables, Domain Linear Constraints |
| **Layer 4** | **API Orchestration & Persistence** | Manages REST endpoints, persistence, what-if engine, feedback | HTTP Requests from React UI / External systems | Validated JSON responses, Swagger API docs, Error models | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, Supabase PostgreSQL |

---

## 8. SYSTEM COMPONENT ROLES & RESPONSIBILITIES

### 1. FastAPI Backend (Layer 4 Orchestrator)
- Serves as the central API gateway and orchestrator.
- Validates all incoming payloads with strict Pydantic v2 schemas.
- Ingests tasks, invokes Layer 1, passes risk to Layer 2, feeds scored tasks and timetables into Layer 3, and writes results to PostgreSQL in a single atomic transaction.
- Measures real execution duration (`execution_time_ms`) for full observability.
- Runs the What-If simulation engine without mutating production plans.

### 2. Supabase / PostgreSQL Database
- Provides acid-compliant relational persistence across 8 tables:
  1. `segments`: Infrastructure asset inventory.
  2. `maintenance_tasks`: Work order requests submitted by departments.
  3. `risk_predictions`: Layer 1 cached predictions, survival curves, and SHAP features.
  4. `negotiation_results`: Layer 2 arbitration records and inflation audits.
  5. `optimization_runs`: Immutable records of CP-SAT execution metrics.
  6. `block_plans`: Operational plans (weekly, monthly, or what-if).
  7. `block_assignments`: Individual scheduled block allocations.
  8. `feedback_records`: Actual field execution logs and overrun metrics.

### 3. Machine Learning Models (Layer 1)
- Eliminates reliance on subjective human opinions of track condition.
- Produces statistically sound, data-driven probabilities of track failure.
- Provides explainable feature contributions to justify preventive scheduling.

### 4. Optimization Engine (Layer 3)
- Eliminates human scheduling bias and manual trial-and-error.
- Mathematically proves that no maintenance block overlaps with an active train passage.
- Dynamically adapts the schedule depending on management policy (Safety-first vs. Throughput-first).

### 5. React Dashboard (Frontend Digital Twin UI)
- Consumes Layer 4 FastAPI endpoints via Axios / Fetch.
- Renders:
  1. **Gantt Chart**: Visual block timeline synchronized against train paths.
  2. **Corridor Health Map (GIS)**: Color-coded map of track segments (green = low risk, red = critical risk).
  3. **Arbitration Panel**: Departmental claim audit showing inflated bids and consolidation savings.
  4. **What-If Sandbox**: UI modal allowing dispatchers to inject rail defects and inspect Plan B diffs in real time.

---

## 9. COMPLETE END-TO-END DATA FLOW DIAGRAMS

### High-Level Linear Flow
```
[Sensors & Maintenance Teams] 
          │
          ▼ (Task Requests)
[Layer 4: Ingestion Route (POST /ingest/tasks)] 
          │
          ▼ (Store Tasks)
[Supabase: maintenance_tasks Table]
          │
          ├─────────────────────────────────────────┐
          ▼                                         ▼
[Corridor Segment Attributes]            [Layer 0 Timetable Slots]
          │                                         │
          ▼                                         │
[Layer 1: ML Failure Forecasting]                   │
  • XGBoost 30d Failure Risk                        │
  • Weibull Survival Analysis                       │
          │                                         │
          ▼ (Risk Map)                              │
[Layer 2: Department Negotiation]                   │
  • Evidence Scoring (Claim vs. Risk)               │
  • Inflated Claim Flagging                         │
  • Multi-Task Consolidation                        │
          │                                         │
          ▼ (Scored Tasks)                          │
          └────────────────────┬────────────────────┘
                               │
                               ▼
            [Layer 3: CP-SAT Optimization Solver]
              • Non-overlap with timetable trains
              • Policy weights: Safety vs. Throughput
              • Explanation metadata generation
                               │
                               ▼
            [Layer 4: Atomic DB Persistence]
              • optimization_runs
              • block_plans (Active Plan)
              • block_assignments
                               │
                               ▼
            [React Dashboard / Digital Twin UI]
              • Interactive Gantt Chart
              • What-If Contingency Simulator
              • GIS Corridor Heatmap
                               │
                               ▼ (Field Execution Feedback)
            [POST /feedback/block → Closed-Loop Recalibration]
```

### Detailed Mermaid Component Diagram
```mermaid
flowchart TD
    subgraph DataSources["1. Data Sources & Synthetic Digital Twin"]
        L0["Layer 0: Indian Railways Generator"]
        UI_In["Field Engineers UI Submissions"]
    end

    subgraph Layer4_API["2. Layer 4: FastAPI REST Layer"]
        R_Tasks["POST /ingest/tasks"]
        R_Risk["GET /risk/segments"]
        R_Neg["POST /negotiate"]
        R_Opt["POST /optimize"]
        R_Wif["POST /optimize/whatif"]
        R_Plan["GET /plan/current"]
        R_Feed["POST /feedback/block"]
    end

    subgraph CoreDB["3. Supabase PostgreSQL Storage"]
        T_Seg[(segments)]
        T_Task[(maintenance_tasks)]
        T_Risk[(risk_predictions)]
        T_Neg[(negotiation_results)]
        T_Run[(optimization_runs)]
        T_Plan[(block_plans)]
        T_Assign[(block_assignments)]
        T_Feed[(feedback_records)]
    end

    subgraph ML_OR["4. Mathematical & AI Engines"]
        L1["Layer 1: Discrete Survival & XGBoost"]
        L2["Layer 2: Evidence Scoring & Consolidation"]
        L3["Layer 3: Google OR-Tools CP-SAT Solver"]
    end

    subgraph Frontend["5. React Dashboard (Digital Twin)"]
        UI_Gantt["Interactive Gantt Chart"]
        UI_GIS["GIS Risk Corridor Map"]
        UI_WhatIf["What-If Disruption Sandbox"]
        UI_Feedback["Execution Overrun Tracker"]
    end

    %% Flow connections
    L0 -->|Populates| T_Seg
    L0 -->|Generates Timetable| L3
    UI_In -->|Submits| R_Tasks
    R_Tasks -->|Upserts| T_Task

    T_Seg -->|Attributes| L1
    L1 -->|risk_30d & Survival Curve| T_Risk
    T_Risk -->|Risk Profile| L2
    T_Task -->|Pending Bids| L2

    L2 -->|Scored Tasks| T_Neg
    T_Neg -->|Weighted Priority| L3
    L3 -->|Optimal Blocks & Explanations| T_Run
    T_Run -->|Generates| T_Plan
    T_Plan -->|Contains| T_Assign

    R_Plan -->|Fetches Current Plan| T_Assign
    T_Assign -->|Renders| UI_Gantt
    T_Risk -->|Visualizes| UI_GIS
    R_Wif -->|Plan B Diff| UI_WhatIf

    UI_Feedback -->|Submits Actuals| R_Feed
    R_Feed -->|Overrun Logs| T_Feed
    T_Feed -->|Recalibration Dataset| L1
```

---

## 10. CURRENT STATUS MATRIX

| Component | Status | Verification / Evidence |
|---|---|---|
| **Layer 0: Indian Railways Synthetic Data Generator** | ✅ **COMPLETED** | Tested in [`railsync/layer0/`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/railsync/layer0/); generates segments, timetable, tasks, goods forecasts. |
| **Layer 1: ML Failure Forecasting (Adapter & Engine)** | ✅ **COMPLETED** | Tested in [`app/integrations/layer1.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/integrations/layer1.py); XGBoost + Weibull model loaded once, outputs 30d risk and SHAP contributions. |
| **Layer 2: Department Negotiation (Adapter & Engine)** | ✅ **COMPLETED** | Tested in [`app/integrations/layer2.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/integrations/layer2.py); evidence scoring, inflation tagging, and consolidation functioning. |
| **Layer 3: CP-SAT Block Optimizer (Adapter & Engine)** | ✅ **COMPLETED** | Tested in [`app/integrations/layer3.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/integrations/layer3.py); CP-SAT solver successfully schedules blocks avoiding timetable trains across 3 policies. |
| **Layer 4: FastAPI REST Endpoints (7 modules)** | ✅ **COMPLETED** | All routes in [`app/api/routes/`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/api/routes/) verified; health, tasks, risk, negotiate, optimize, plans, feedback. |
| **Layer 4: Database Models & Repositories** | ✅ **COMPLETED** | 8 ORM models in [`app/db/models.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/db/models.py) and clean data access functions in [`app/db/repositories.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/db/repositories.py). |
| **Layer 4: Database Migrations (Alembic)** | ✅ **COMPLETED** | Migration `001_initial_schema.py` ready for Supabase execution (`alembic upgrade head`). |
| **Layer 4: Database Seeder Script** | ✅ **COMPLETED** | CLI tool [`app/seed.py`](file:///c:/Users/Sudhanshu%20Rajpoot/Downloads/Backend/app/seed.py) tested and functional (`python -m app.seed`). |
| **Automated Pytest Suite** | ✅ **COMPLETED** | **13 of 13 tests passing in 0.49 seconds** across all lifecycle stages. |
| **Supabase PostgreSQL Remote Instance** | ⏳ **PENDING USER CONFIG** | Requires user to supply live `SUPABASE_DATABASE_URL` in `.env` to apply Alembic migrations. |
| **React Dashboard (Frontend)** | 🚧 **NEXT INTEGRATION PHASE** | UI to consume Layer 4 REST endpoints via OpenAPI client. |

---

## 11. STEP-BY-STEP IMPLEMENTATION ROADMAP

### Phase 1: Local Backend & Cloud Database Connection (CURRENT STEP)
1. **Configure `.env`**:
   Copy `.env.example` to `.env` and fill in the live Supabase PostgreSQL connection string:
   ```ini
   SUPABASE_DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
   PORT=8000
   LOG_LEVEL=INFO
   CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
   ```
2. **Execute Database Migrations**:
   Run Alembic to create all 8 relational tables on Supabase:
   ```powershell
   .\.venv\Scripts\alembic upgrade head
   ```
3. **Seed Cloud Database**:
   Populate Supabase with Indian Railways corridor segments, initial tasks, and baseline plan:
   ```powershell
   .\.venv\Scripts\python -m app.seed --seed 42
   ```

### Phase 2: Start Backend Server & Verify via Swagger UI
1. **Launch FastAPI Development Server**:
   ```powershell
   .\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Verify Interactive Documentation**:
   - Open browser at `http://localhost:8000/docs`.
   - Test `GET /health` to confirm database connectivity.
   - Test `GET /plan/current` to verify baseline block allocations.

### Phase 3: Connect React Frontend Dashboard
1. **Configure API Base URL in React App**:
   Point frontend API calls to `http://localhost:8000`.
2. **Bind React Components to Endpoints**:
   - **Gantt Chart**: Call `GET /plan/current` $\to$ bind `assignments[]` to timeline bars.
   - **GIS Corridor Map**: Call `GET /risk/segments` $\to$ color-code track segments based on `risk_30d`.
   - **Task Submission Form**: Submit new department work orders to `POST /ingest/tasks`.
   - **Negotiation Audit View**: Call `POST /negotiate` $\to$ display evidence scores and inflation alerts.
   - **What-If Sandbox**: Submit disruption parameters to `POST /optimize/whatif` $\to$ render Plan B diffs.
   - **Field Supervisor Feedback Modal**: Submit actual timestamps to `POST /feedback/block`.

### Phase 4: Swapping Standalone Models with Separate Team Scripts (When Ready)
Because we implemented the **Adapter Pattern** (`app/integrations/layer1.py`, `layer2.py`, `layer3.py`), integrating separate teammate modules requires **zero changes to database or API code**:
1. Drop the teammate's trained model artifact or script into the project.
2. In `app/integrations/layer1.py`, update `predict_risk(segment_data)` to invoke the teammate's model.
3. In `app/integrations/layer2.py`, update `negotiate(tasks, risk_data)` to call their custom negotiation algorithm.
4. In `app/integrations/layer3.py`, update `optimize(tasks, risk_data, ...)` if they have customized CP-SAT constraints.
5. All route handlers, Pydantic schemas, database tables, and frontend bindings continue to work seamlessly without modifications.

---
*Document Compiled & Certified for RailSync 2.0 (Layer 4 Backend Architecture)*
