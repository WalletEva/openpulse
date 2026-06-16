"""Task repository - CRUD operations for collection tasks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CollectionRun, CollectionTask


class TaskRepository:
    """Repository for collection task data access."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, task: CollectionTask) -> CollectionTask:
        """Add a new collection task."""
        self.session.add(task)
        self.session.flush()
        return task

    def get_by_id(self, task_id: int) -> CollectionTask | None:
        """Get a task by its ID."""
        stmt = select(CollectionTask).where(CollectionTask.id == task_id)
        return self.session.scalars(stmt).first()

    def get_by_name(self, name: str) -> CollectionTask | None:
        """Get a task by its name."""
        stmt = select(CollectionTask).where(CollectionTask.name == name)
        return self.session.scalars(stmt).first()

    def list_all(
        self,
        enabled: bool | None = None,
        source_id: int | None = None,
    ) -> list[CollectionTask]:
        """List all tasks with optional filters."""
        stmt = select(CollectionTask)

        if enabled is not None:
            stmt = stmt.where(CollectionTask.enabled == enabled)
        if source_id is not None:
            stmt = stmt.where(CollectionTask.source_id == source_id)

        stmt = stmt.order_by(CollectionTask.name.asc())
        return list(self.session.scalars(stmt).all())

    def update(self, task_id: int, **kwargs: Any) -> CollectionTask | None:
        """Update a task configuration."""
        task = self.get_by_id(task_id)
        if not task:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        self.session.flush()
        return task

    def delete(self, task_id: int) -> bool:
        """Delete a task."""
        task = self.get_by_id(task_id)
        if not task:
            return False
        self.session.delete(task)
        self.session.flush()
        return True

    def record_run(
        self,
        task_id: int,
        trigger_type: str = "scheduled",
    ) -> CollectionRun:
        """Create a new run record for a task."""
        run = CollectionRun(
            task_id=task_id,
            started_at=datetime.utcnow(),
            trigger_type=trigger_type,
        )
        self.session.add(run)
        self.session.flush()
        return run

    def finish_run(
        self,
        run_id: int,
        success: bool = True,
        articles_collected: int = 0,
        articles_new: int = 0,
        error_message: str | None = None,
    ) -> CollectionRun | None:
        """Mark a run as finished with results."""
        stmt = select(CollectionRun).where(CollectionRun.id == run_id)
        run = self.session.scalars(stmt).first()
        if not run:
            return None

        run.finished_at = datetime.utcnow()
        run.duration_seconds = (run.finished_at - run.started_at).total_seconds()
        run.success = success
        run.articles_collected = articles_collected
        run.articles_new = articles_new
        run.error_message = error_message

        # Update task's last_run_at
        task = self.get_by_id(run.task_id)
        if task:
            task.last_run_at = run.started_at

        self.session.flush()
        return run

    def get_recent_runs(self, task_id: int, limit: int = 10) -> list[CollectionRun]:
        """Get recent run records for a task."""
        stmt = (
            select(CollectionRun)
            .where(CollectionRun.task_id == task_id)
            .order_by(CollectionRun.started_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
