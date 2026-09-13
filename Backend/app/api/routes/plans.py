"""RailSync 2.0 — Plan retrieval endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.plans import PlanResponse
from app.services import plan_service

router = APIRouter(tags=["Plans"])


@router.get("/plan/current", response_model=PlanResponse)
def get_current_plan(db: Session = Depends(get_db)):
    plan = plan_service.get_current_plan(db)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current plan exists. Run POST /optimize first.",
        )
    return plan


@router.get("/plan/{plan_id}", response_model=PlanResponse)
def get_plan_by_id(plan_id: str, db: Session = Depends(get_db)):
    plan = plan_service.get_plan_by_id(db, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found",
        )
    return plan
