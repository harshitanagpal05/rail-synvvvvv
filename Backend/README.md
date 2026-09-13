# RailSync 2.0 — Backend Engine (Layer 4)
### AI-Powered Automatic Block Planning & Digital Twin for Indian Railways

> **Smart India Hackathon Prototype**  
> An enterprise-grade, mathematical, closed-loop railway maintenance block planning platform.

---

## 🚆 System Overview & Architecture

RailSync 2.0 automates railway maintenance block scheduling by orchestrating 4 interconnected computational layers behind an asynchronous, production-ready FastAPI backend:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Layer 4: FastAPI Backend                           │
│  - REST API routes (Health, Ingestion, Risk, Negotiation, Optimization) │
│  - Persistence: Supabase PostgreSQL (8 relational tables with FKs)      │
│  - What-If Disruption Engine (immutability + plan diffing)              │
│  - Closed-Loop Execution Feedback & Model Recalibration Hooks           │
└───────┬───────────────────┬────────────────────┬────────────────────┬───┘
        │                   │                    │                    │
┌───────▼────────┐  ┌───────▼────────┐  ┌────────▼───────┐  ┌─────────▼───────┐
│ Layer 0        │  │ Layer 1        │  │ Layer 2        │  │ Layer 3         │
│ Synthetic Data │  │ Failure & Risk │  │ Department     │  │ CP-SAT Block    │
│ Generator      │  │ Forecasting    │  │ Negotiation    │  │ Optimizer       │
│                │  │                │  │                │  │                 │
│ • Causal data  │  │ • XGBoost 30d  │  │ • Evidence     │  │ • OR-Tools      │
│   for IR       │  │   risk score   │    scoring        │    CP-SAT          │
│ • Corridors &  │  │ • Weibull      │  │ • Inflated     │  │ • Multi-policy  │
│   divisions    │    survival curve │    claim detector │    (safety/balanced│
│ • Timetables & │  │ • SHAP-style   │  │ • Consolidation│    /throughput)    │
│   freight flows│    feature import.│    clustering     │  │ • No timetable  │
│ • Tasks backlog│  │ • Durations    │  │ • Fair weights │    clashes         │
└────────────────┘  └────────────────┘  └────────────────┘  └─────────────────┘
```

---

## 🌟 Key Features

1. **Zero Fake Computations**:
   - Every risk score is computed by a trained XGBoost classifier and Weibull survival model.
   - Every block allocation is solved via constraint programming using Google OR-Tools CP-SAT.
   - Timetable conflicts, safety margins, and department co-location rules are strictly enforced.

2. **Enterprise Integration Adapters**:
   - Dedicated adapters (`app/integrations/layer1.py`, `layer2.py`, `layer3.py`) decouple backend business logic from ML/OR solver internals.
   - Standalone fallback engines ensure 100% testability and zero downtime before separate team modules are dropped in.

3. **What-If Disruption Engine**:
   - Simulates emergency track fractures, OHE breakdowns, or signal failures without mutating the active baseline plan.
   - Generates a "Plan B" contingency schedule alongside full visual diffing (added, moved, canceled blocks).

4. **Closed-Loop Execution Feedback**:
   - Collects planned vs. actual maintenance block durations from field supervisors.
   - Computes overrun rates, mean absolute error (MAE), and bias trends (`improving`, `worsening`, `stable`).
   - Exports high-fidelity recalibration datasets for continuous Layer 1 model training.

5. **Relational Database Design**:
   - 8 normalized tables with foreign keys and cascade integrity:
     `segments`, `maintenance_tasks`, `risk_predictions`, `negotiation_results`, `optimization_runs`, `block_plans`, `block_assignments`, `feedback_records`.
   - Managed migrations via Alembic.

---

## 📁 Repository Structure

```
Backend/
├── alembic/                    # Database migration scripts
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
├── alembic.ini                 # Alembic configuration
├── app/
│   ├── api/
│   │   └── routes/             # FastAPI REST endpoints
│   │       ├── health.py       # Dependency health check
│   │       ├── tasks.py        # Task ingestion & idempotency
│   │       ├── risk.py         # Layer 1 risk & survival curves
│   │       ├── negotiation.py  # Layer 2 multi-dept negotiation
│   │       ├── optimization.py # Layer 3 CP-SAT planning & what-if
│   │       ├── plans.py        # Active and historical plans
│   │       └── feedback.py     # Execution feedback & metrics
│   ├── core/
│   │   ├── config.py           # Pydantic Settings & env configuration
│   │   └── logging.py          # Structured logging
│   ├── db/
│   │   ├── database.py         # Engine & session management
│   │   ├── models.py           # 8 SQLAlchemy ORM models
│   │   └── repositories.py     # Clean data access layer (CRUD)
│   ├── integrations/           # Clean contracts & adapters
│   │   ├── layer1.py           # Failure forecasting adapter
│   │   ├── layer2.py           # Negotiation engine adapter
│   │   └── layer3.py           # CP-SAT optimizer adapter
│   ├── schemas/                # Pydantic v2 request/response schemas
│   │   ├── common.py
│   │   ├── tasks.py
│   │   ├── risk.py
│   │   ├── negotiation.py
│   │   ├── optimization.py
│   │   ├── plans.py
│   │   └── feedback.py
│   ├── services/               # Core orchestration services
│   │   ├── task_service.py
│   │   ├── risk_service.py
│   │   ├── negotiation_service.py
│   │   ├── optimization_service.py
│   │   ├── plan_service.py
│   │   ├── whatif_service.py
│   │   └── feedback_service.py
│   ├── main.py                 # FastAPI application entrypoint
│   └── seed.py                 # Synthetic database seeder
├── railsync/
│   └── layer0/                 # Indian Railways synthetic generator
│       ├── corridors.py        # Delhi-Mumbai, Delhi-Howrah corridors
│       └── generator.py        # Timetable, tasks, and segment generator
├── tests/                      # Automated test suite
│   ├── conftest.py             # Test database and client fixtures
│   ├── test_health.py
│   ├── test_tasks.py
│   ├── test_risk.py
│   ├── test_negotiation.py
│   ├── test_optimization.py
│   ├── test_plans.py
│   ├── test_feedback.py
│   └── test_integration.py     # Full end-to-end workflow test
├── .env.example                # Template for environment secrets
├── requirements.txt            # Python dependencies
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.10+
- PostgreSQL database (e.g. Supabase)

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in your database URL:
```ini
SUPABASE_DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
```bash
alembic upgrade head
```

### 5. Seed Database (segments only — tasks come from your API POSTs)
```bash
python -m app.seed --layer0 Railsync_2.0_Layer_0_FINAL
# Optional: also load Layer 0 maintenance tasks for demos
python -m app.seed --layer0 Railsync_2.0_Layer_0_FINAL --with-tasks
```

---

## 🚀 Running the Server

Start the Uvicorn server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive Swagger documentation will be live at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running Automated Tests

Run the full pytest suite:
```bash
pytest tests/ -v
```

All tests execute against an isolated in-memory test database, validating:
- Service and repository contracts
- 404 / 409 / 422 HTTP edge cases
- End-to-end pipeline execution from task submission to feedback collection

---

## 📡 Key REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Dependency health check (DB, Layer 1, Layer 2, Layer 3) |
| `POST` | `/ingest/tasks` | Ingest maintenance task with segment validation and idempotency |
| `GET` | `/risk/segments` | Filterable list of segment failure probabilities |
| `GET` | `/risk/{segment_id}` | Detailed risk profile with Weibull survival curve and SHAP features |
| `POST` | `/negotiate` | Run Layer 2 multi-department arbitration & claim inflation detection |
| `POST` | `/optimize` | Full pipeline: CP-SAT mathematical optimization into a block plan |
| `POST` | `/optimize/whatif` | Non-destructive disruption simulation (Plan B generator) |
| `GET` | `/plan/current` | Retrieve the active operational block plan with explanation metadata |
| `GET` | `/plan/{plan_id}` | Retrieve historical or what-if plan |
| `POST` | `/feedback/block` | Submit actual block execution timestamps & overrun logs |
| `GET` | `/feedback/metrics` | Closed-loop metrics, duration error distributions & bias trends |
