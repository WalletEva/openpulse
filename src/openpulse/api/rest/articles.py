"""REST API - Articles router."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from openpulse.storage.database import get_session
from openpulse.storage.repositories.article_repo import ArticleRepository

router = APIRouter(tags=["articles"])


class ArticleResponse(BaseModel):
    id: str
    title: str
    source: str
    source_type: str
    url: str
    author: str
    published_at: str | None
    collected_at: str
    language: str
    tags: list[str]
    summary: str


class ArticleDetailResponse(ArticleResponse):
    content: str
    image_url: str
    raw_data: dict[str, Any]


class CollectRequest(BaseModel):
    source_name: str | None = None
    rsshub_route: str | None = None
    feed_url: str | None = None
    limit: int = Field(default=50, ge=1, le=500)


class CollectResponse(BaseModel):
    source: str
    total_collected: int
    new_articles: int
    articles: list[ArticleResponse]


@router.get("/articles")
async def list_articles(
    q: str | None = Query(None, description="Search query"),
    source: str | None = Query(None, description="Filter by source name"),
    source_type: str | None = Query(None, description="Filter by source type"),
    language: str | None = Query(None, description="Filter by language"),
    since: str | None = Query(None, description="Published after (ISO date)"),
    until: str | None = Query(None, description="Published before (ISO date)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[ArticleResponse]:
    """Search and list articles with filters."""
    session = get_session()
    try:
        repo = ArticleRepository(session)
        articles = repo.search(
            query=q,
            source=source,
            source_type=source_type,
            language=language,
            since=datetime.fromisoformat(since) if since else None,
            until=datetime.fromisoformat(until) if until else None,
            limit=limit,
            offset=offset,
        )
        return [
            ArticleResponse(
                id=a.id,
                title=a.title,
                source=a.source,
                source_type=a.source_type or "rss",
                url=a.url or "",
                author=a.author or "",
                published_at=a.published_at.isoformat() if a.published_at else None,
                collected_at=a.collected_at.isoformat() if a.collected_at else "",
                language=a.language or "auto",
                tags=a.tags or [],
                summary=a.summary or "",
            )
            for a in articles
        ]
    finally:
        session.close()


@router.get("/articles/{article_id}")
async def get_article(article_id: str) -> ArticleDetailResponse:
    """Get a single article by ID."""
    session = get_session()
    try:
        repo = ArticleRepository(session)
        a = repo.get_by_id(article_id)
        if not a:
            raise HTTPException(status_code=404, detail="Article not found")
        return ArticleDetailResponse(
            id=a.id,
            title=a.title,
            source=a.source,
            source_type=a.source_type or "rss",
            url=a.url or "",
            author=a.author or "",
            published_at=a.published_at.isoformat() if a.published_at else None,
            collected_at=a.collected_at.isoformat() if a.collected_at else "",
            language=a.language or "auto",
            tags=a.tags or [],
            summary=a.summary or "",
            content=a.content or "",
            image_url=a.image_url or "",
            raw_data=a.raw_data or {},
        )
    finally:
        session.close()


@router.get("/articles/count")
async def count_articles(
    source: str | None = Query(None),
    source_type: str | None = Query(None),
    language: str | None = Query(None),
) -> dict[str, int]:
    """Count articles matching filters."""
    session = get_session()
    try:
        repo = ArticleRepository(session)
        return {"count": repo.count(source=source, source_type=source_type, language=language)}
    finally:
        session.close()


@router.post("/collect")
async def trigger_collect(req: CollectRequest) -> CollectResponse:
    """Trigger an immediate collection run."""
    import asyncio
    from openpulse.collector.adapters import CustomRSSCollector, RSSHubCollector
    from openpulse.collector.converter import pydantic_list_to_orm
    from openpulse.storage.repositories.source_repo import SourceRepository

    async def _collect():
        if req.rsshub_route:
            collector = RSSHubCollector()
            config = {"route": req.rsshub_route, "limit": req.limit, "source_name": req.rsshub_route}
        elif req.feed_url:
            collector = CustomRSSCollector()
            config = {"url": req.feed_url, "limit": req.limit, "source_name": req.feed_url}
        elif req.source_name:
            session = get_session()
            try:
                repo = SourceRepository(session)
                src = repo.get_by_name(req.source_name)
            finally:
                session.close()
            if not src:
                raise HTTPException(status_code=404, detail=f"Source '{req.source_name}' not found")
            config = {**(src.config or {}), "source_name": src.name, "limit": req.limit}
            if src.adapter == "rsshub":
                collector = RSSHubCollector()
            else:
                collector = CustomRSSCollector()
        else:
            raise HTTPException(status_code=400, detail="Provide source_name, rsshub_route, or feed_url")

        result = await collector.collect(config)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        orm_articles = pydantic_list_to_orm(result.articles)
        session = get_session()
        try:
            article_repo = ArticleRepository(session)
            new_articles = article_repo.add_many(orm_articles)
            session.commit()
        finally:
            session.close()

        return CollectResponse(
            source=result.source,
            total_collected=result.count,
            new_articles=len(new_articles),
            articles=[
                ArticleResponse(
                    id=a.id,
                    title=a.title,
                    source=a.source,
                    source_type=a.source_type or "rss",
                    url=a.url or "",
                    author=a.author or "",
                    published_at=a.published_at.isoformat() if a.published_at else None,
                    collected_at=a.collected_at.isoformat() if a.collected_at else "",
                    language=a.language or "auto",
                    tags=a.tags or [],
                    summary=a.summary[:200] if a.summary else "",
                )
                for a in new_articles[:20]
            ],
        )

    return await _collect()
