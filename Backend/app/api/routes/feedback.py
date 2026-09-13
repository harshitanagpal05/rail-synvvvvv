"""RailSync 2.0 — Feedback endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.feedback import (
    FeedbackCreateRequest,
    FeedbackMetricsResponse,
    FeedbackResponse,
)
from app.services import feedback_service

router = APIRouter(tags=["Feedback"])


@router.post(
    "/feedback/block",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_feedback(request: FeedbackCreateRequest, db: Session = Depends(get_db)):
    try:
        return feedback_service.record_feedback(db, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/feedback/metrics", response_model=FeedbackMetricsResponse)
def get_metrics(db: Session = Depends(get_db)):
    return feedback_service.compute_metrics(db)
