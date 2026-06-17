"""REST API - Watchlists router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from openpulse.storage.database import get_session
from openpulse.storage.models import Watchlist

router = APIRouter(tags=["watchlists"])


class WatchlistResponse(BaseModel):
    id: int
    keyword: str
    category: str
    enabled: bool
    match_count: int
    last_matched_at: str | None


class WatchlistAddRequest(BaseModel):
    keywords: list[str] = Field(description="List of keywords to add")
    category: str = Field(default="")


class WatchlistAddResponse(BaseModel):
    added: list[str]
    total: int


@router.get("/watchlists")
async def list_watchlists(
    category: str | None = None,
    enabled: bool | None = None,
) -> list[WatchlistResponse]:
    """List all watchlist items."""
    session = get_session()
    try:
        stmt = select(Watchlist).order_by(Watchlist.keyword.asc())
        if category:
            stmt = stmt.where(Watchlist.category == category)
        if enabled is not None:
            stmt = stmt.where(Watchlist.enabled == enabled)
        items = list(session.scalars(stmt).all())
        return [
            WatchlistResponse(
                id=w.id,
                keyword=w.keyword,
                category=w.category or "",
                enabled=w.enabled,
                match_count=w.match_count,
                last_matched_at=w.last_matched_at.isoformat() if w.last_matched_at else None,
            )
            for w in items
        ]
    finally:
        session.close()


@router.post("/watchlists")
async def add_watchlist(req: WatchlistAddRequest) -> WatchlistAddResponse:
    """Add keywords to the watchlist."""
    session = get_session()
    try:
        added = []
        for kw in req.keywords:
            existing = session.scalar(
                select(Watchlist).where(Watchlist.keyword == kw)
            )
            if not existing:
                w = Watchlist(keyword=kw, category=req.category)
                session.add(w)
                added.append(kw)
        session.commit()
        total = session.scalar(select(Watchlist).count()) or 0
        return WatchlistAddResponse(added=added, total=total)
    finally:
        session.close()


@router.delete("/watchlists/{item_id}")
async def delete_watchlist_item(item_id: int) -> dict:
    """Delete a watchlist item."""
    session = get_session()
    try:
        w = session.scalar(select(Watchlist).where(Watchlist.id == item_id))
        if not w:
            raise HTTPException(status_code=404, detail="Watchlist item not found")
        session.delete(w)
        session.commit()
        return {"deleted": item_id}
    finally:
        session.close()
