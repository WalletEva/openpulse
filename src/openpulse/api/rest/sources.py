"""REST API - Sources router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openpulse.storage.database import get_session
from openpulse.storage.models import Source
from openpulse.storage.repositories.source_repo import SourceRepository

router = APIRouter(tags=["sources"])


class SourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    adapter: str
    category: str
    language: str
    enabled: bool
    config: dict[str, Any]


class SourceCreateRequest(BaseModel):
    name: str = Field(description="Unique source name")
    source_type: str = Field(default="rss", description="Source type: rsshub, rss, api, social")
    adapter: str = Field(default="custom_rss", description="Adapter: rsshub, custom_rss, newsapi")
    config: dict[str, Any] = Field(default_factory=dict, description="Adapter-specific config")
    category: str = Field(default="", description="Category: news, tech, social, etc.")
    language: str = Field(default="auto")


@router.get("/sources")
async def list_sources(
    category: str | None = None,
    enabled: bool | None = None,
    source_type: str | None = None,
) -> list[SourceResponse]:
    """List all configured sources."""
    session = get_session()
    try:
        repo = SourceRepository(session)
        sources = repo.list_all(category=category, enabled=enabled, source_type=source_type)
        return [
            SourceResponse(
                id=s.id,
                name=s.name,
                source_type=s.source_type,
                adapter=s.adapter,
                category=s.category or "",
                language=s.language or "auto",
                enabled=s.enabled,
                config=s.config or {},
            )
            for s in sources
        ]
    finally:
        session.close()


@router.post("/sources")
async def create_source(req: SourceCreateRequest) -> SourceResponse:
    """Create a new source configuration."""
    session = get_session()
    try:
        repo = SourceRepository(session)
        existing = repo.get_by_name(req.name)
        if existing:
            raise HTTPException(status_code=409, detail=f"Source '{req.name}' already exists")
        src = repo.add(Source(
            name=req.name,
            source_type=req.source_type,
            adapter=req.adapter,
            config=req.config,
            category=req.category,
            language=req.language,
        ))
        session.commit()
        return SourceResponse(
            id=src.id,
            name=src.name,
            source_type=src.source_type,
            adapter=src.adapter,
            category=src.category or "",
            language=src.language or "auto",
            enabled=src.enabled,
            config=src.config or {},
        )
    finally:
        session.close()


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int) -> dict:
    """Delete a source configuration."""
    session = get_session()
    try:
        repo = SourceRepository(session)
        if not repo.delete(source_id):
            raise HTTPException(status_code=404, detail="Source not found")
        session.commit()
        return {"deleted": source_id}
    finally:
        session.close()


@router.patch("/sources/{source_id}/toggle")
async def toggle_source(source_id: int) -> SourceResponse:
    """Toggle a source's enabled state."""
    session = get_session()
    try:
        repo = SourceRepository(session)
        src = repo.toggle_enabled(source_id)
        if not src:
            raise HTTPException(status_code=404, detail="Source not found")
        session.commit()
        return SourceResponse(
            id=src.id,
            name=src.name,
            source_type=src.source_type,
            adapter=src.adapter,
            category=src.category or "",
            language=src.language or "auto",
            enabled=src.enabled,
            config=src.config or {},
        )
    finally:
        session.close()
