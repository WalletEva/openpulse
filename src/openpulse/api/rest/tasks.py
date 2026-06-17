"""REST API - Tasks router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openpulse.storage.database import get_session
from openpulse.storage.models import CollectionTask
from openpulse.storage.repositories.task_repo import TaskRepository

router = APIRouter(tags=["tasks"])


class TaskResponse(BaseModel):
    id: int
    name: str
    source_id: int
    cron_expr: str | None
    enabled: bool
    max_articles: int
    last_run_at: str | None
    next_run_at: str | None


class TaskCreateRequest(BaseModel):
    name: str
    source_id: int
    cron_expr: str = Field(description="Cron expression (e.g. '*/30 * * * *')")
    max_articles: int = 50


class RunResponse(BaseModel):
    id: int
    task_id: int
    started_at: str
    finished_at: str | None
    duration_seconds: float | None
    articles_collected: int
    articles_new: int
    success: bool
    error_message: str | None
    trigger_type: str


@router.get("/tasks")
async def list_tasks(
    enabled: bool | None = None,
    source_id: int | None = None,
) -> list[TaskResponse]:
    """List all collection tasks."""
    session = get_session()
    try:
        repo = TaskRepository(session)
        tasks = repo.list_all(enabled=enabled, source_id=source_id)
        return [
            TaskResponse(
                id=t.id,
                name=t.name,
                source_id=t.source_id,
                cron_expr=t.cron_expr,
                enabled=t.enabled,
                max_articles=t.max_articles,
                last_run_at=t.last_run_at.isoformat() if t.last_run_at else None,
                next_run_at=t.next_run_at.isoformat() if t.next_run_at else None,
            )
            for t in tasks
        ]
    finally:
        session.close()


@router.post("/tasks")
async def create_task(req: TaskCreateRequest) -> TaskResponse:
    """Create a new collection task."""
    session = get_session()
    try:
        repo = TaskRepository(session)
        existing = repo.get_by_name(req.name)
        if existing:
            raise HTTPException(status_code=409, detail=f"Task '{req.name}' already exists")
        task = repo.add(CollectionTask(
            name=req.name,
            source_id=req.source_id,
            cron_expr=req.cron_expr,
            max_articles=req.max_articles,
        ))
        session.commit()
        return TaskResponse(
            id=task.id,
            name=task.name,
            source_id=task.source_id,
            cron_expr=task.cron_expr,
            enabled=task.enabled,
            max_articles=task.max_articles,
            last_run_at=task.last_run_at.isoformat() if task.last_run_at else None,
            next_run_at=task.next_run_at.isoformat() if task.next_run_at else None,
        )
    finally:
        session.close()


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int) -> dict:
    """Delete a collection task."""
    session = get_session()
    try:
        repo = TaskRepository(session)
        if not repo.delete(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        session.commit()
        return {"deleted": task_id}
    finally:
        session.close()


@router.get("/tasks/{task_id}/runs")
async def get_task_runs(task_id: int, limit: int = 10) -> list[RunResponse]:
    """Get recent run history for a task."""
    session = get_session()
    try:
        repo = TaskRepository(session)
        runs = repo.get_recent_runs(task_id, limit=limit)
        return [
            RunResponse(
                id=r.id,
                task_id=r.task_id,
                started_at=r.started_at.isoformat(),
                finished_at=r.finished_at.isoformat() if r.finished_at else None,
                duration_seconds=r.duration_seconds,
                articles_collected=r.articles_collected,
                articles_new=r.articles_new,
                success=r.success,
                error_message=r.error_message,
                trigger_type=r.trigger_type,
            )
            for r in runs
        ]
    finally:
        session.close()
