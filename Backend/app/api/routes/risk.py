"""RailSync 2.0 — Risk prediction endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.risk import RiskPredictionResponse, SegmentRiskSummary
from app.services import risk_service

router = APIRouter(tags=["Risk"])


@router.get("/risk/segments", response_model=list[SegmentRiskSummary])
def get_all_risks(
    min_risk: float = Query(default=0.0, ge=0.0, le=1.0, description="Filter by minimum risk_30d"),
    division: str = Query(default=None, description="Filter by division"),
    db: Session = Depends(get_db),
):
    risks = risk_service.get_all_segment_risks(db)

    if min_risk > 0:
        risks = [r for r in risks if r.risk_30d >= min_risk]
    if division:
        risks = [r for r in risks if r.division and r.division.lower() == division.lower()]

    return risks


@router.get("/risk/{segment_id}", response_model=RiskPredictionResponse)
def get_segment_risk(segment_id: str, db: Session = Depends(get_db)):
    try:
        return risk_service.get_segment_risk(db, segment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
