"""RailSync 2.0 — FastAPI application entry point.

AI-Powered Automatic Block Planning & Digital Twin for Indian Railways.
Layer 4: API Orchestration + Persistence + Explanation + What-If + Feedback
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root and Backend directory are on sys.path for Render/Docker/local environments
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
for _p in (_REPO_ROOT, _BACKEND_DIR):
    _ps = str(_p)
    if _ps not in sys.path:
        sys.path.insert(0, _ps)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import feedback, health, live, negotiation, optimization, plans, realtime, risk, tasks
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log.info("RailSync 2.0 Layer 4 starting up")

    # Eagerly verify DB connection at startup
    try:
        from app.db.database import check_db_health
        if check_db_health():
            log.info("Database connection verified")
        else:
            log.warning("Database connection failed — endpoints requiring DB will error")
    except Exception as e:
        log.warning("Database not configured: %s", e)

    yield
    log.info("RailSync 2.0 Layer 4 shutting down")


app = FastAPI(
    title="RailSync 2.0 — Layer 4 API",
    description=(
        "AI-Powered Automatic Block Planning & Digital Twin for Indian Railways.\n\n"
        "Orchestrates Layer 1 (Risk/ML), Layer 2 (Negotiation), and Layer 3 (CP-SAT Optimization) "
        "into a unified REST API for the React Dashboard.\n\n"
        "**Prototype Note:** This system uses synthetic/normalized data for demonstration. "
        "It does not have live production TMS/SMMS/TDMS/COA access."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register direct routes
app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(risk.router)
app.include_router(negotiation.router)
app.include_router(optimization.router)
app.include_router(plans.router)
app.include_router(feedback.router)
app.include_router(live.router)
app.include_router(realtime.router)

# Register /api prefixed routes (for production unified serving without rewrite proxies)
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(tasks.router)
api_router.include_router(risk.router)
api_router.include_router(negotiation.router)
api_router.include_router(optimization.router)
api_router.include_router(plans.router)
api_router.include_router(feedback.router)
api_router.include_router(live.router)
api_router.include_router(realtime.router)
app.include_router(api_router)

# Static frontend serving for production Docker (Single URL deployment)
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    log.info("Mounting static frontend assets from %s", static_dir)
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't hijack API or docs routes
        if full_path.startswith("api") or full_path in ["docs", "openapi.json", "redoc"]:
            return {"detail": "Not Found"}
        target = os.path.join(static_dir, full_path)
        if os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(static_dir, "index.html"))
