"""RailSync 2.0 — Health check endpoint."""

from datetime import datetime

from fastapi import APIRouter

from app.db.database import check_db_health
from app.integrations import layer1, layer2, layer3
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    db_ok = check_db_health()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="ok" if db_ok else "unavailable",
        layer1="available" if layer1.is_available() else "unavailable",
        layer2="available" if layer2.is_available() else "unavailable",
        layer3="available" if layer3.is_available() else "unavailable",
        timestamp=datetime.utcnow(),
    )
