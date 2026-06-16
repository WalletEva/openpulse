"""Source repository - CRUD operations for information sources."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Source


class SourceRepository:
    """Repository for source configuration data access."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, source: Source) -> Source:
        """Add a new source configuration."""
        self.session.add(source)
        self.session.flush()
        return source

    def get_by_id(self, source_id: int) -> Source | None:
        """Get a source by its ID."""
        stmt = select(Source).where(Source.id == source_id)
        return self.session.scalars(stmt).first()

    def get_by_name(self, name: str) -> Source | None:
        """Get a source by its name."""
        stmt = select(Source).where(Source.name == name)
        return self.session.scalars(stmt).first()

    def list_all(
        self,
        category: str | None = None,
        enabled: bool | None = None,
        source_type: str | None = None,
    ) -> list[Source]:
        """List all sources with optional filters."""
        stmt = select(Source)

        if category:
            stmt = stmt.where(Source.category == category)
        if enabled is not None:
            stmt = stmt.where(Source.enabled == enabled)
        if source_type:
            stmt = stmt.where(Source.source_type == source_type)

        stmt = stmt.order_by(Source.name.asc())
        return list(self.session.scalars(stmt).all())

    def update(self, source_id: int, **kwargs: Any) -> Source | None:
        """Update a source configuration."""
        source = self.get_by_id(source_id)
        if not source:
            return None
        for key, value in kwargs.items():
            if hasattr(source, key):
                setattr(source, key, value)
        self.session.flush()
        return source

    def delete(self, source_id: int) -> bool:
        """Delete a source configuration."""
        source = self.get_by_id(source_id)
        if not source:
            return False
        self.session.delete(source)
        self.session.flush()
        return True

    def toggle_enabled(self, source_id: int) -> Source | None:
        """Toggle the enabled state of a source."""
        source = self.get_by_id(source_id)
        if not source:
            return None
        source.enabled = not source.enabled
        self.session.flush()
        return source

    def get_categories(self) -> list[str]:
        """Get all distinct source categories."""
        from sqlalchemy import distinct
        stmt = select(distinct(Source.category)).where(Source.category != "")
        return [row[0] for row in self.session.execute(stmt).all()]
