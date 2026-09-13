"""RailSync 2.0 — Task ingestion endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.tasks import TaskCreateRequest, TaskResponse
from app.services import task_service

router = APIRouter(tags=["Tasks"])


@router.post(
    "/ingest/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Task already existed and was updated"},
        400: {"description": "Invalid task data"},
        404: {"description": "Segment not found"},
    },
)
def ingest_task(request: TaskCreateRequest, response: Response, db: Session = Depends(get_db)):
    try:
        task_data, created = task_service.ingest_task(db, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not created:
        response.status_code = status.HTTP_200_OK
    return task_data


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(db: Session = Depends(get_db)):
    return task_service.get_all_tasks(db)
