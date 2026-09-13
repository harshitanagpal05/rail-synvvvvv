"""RailSync 2.0 — Negotiation endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.negotiation import NegotiationResponse
from app.services import negotiation_service

router = APIRouter(tags=["Negotiation"])


@router.post("/negotiate", response_model=NegotiationResponse)
def run_negotiation(db: Session = Depends(get_db)):
    try:
        return negotiation_service.run_negotiation(db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
