"""REST API - System router."""

from __future__ import annotations

from fastapi import APIRouter

from openpulse import __version__
from openpulse.storage.database import get_session
from openpulse.storage.repositories.article_repo import ArticleRepository
from openpulse.storage.repositories.source_repo import SourceRepository
from openpulse.storage.repositories.task_repo import TaskRepository

router = APIRouter(tags=["system"])


@router.get("/system/status")
async def system_status() -> dict:
    """Get system status and statistics."""
    session = get_session()
    try:
        article_repo = ArticleRepository(session)
        source_repo = SourceRepository(session)
        task_repo = TaskRepository(session)

        total_articles = article_repo.count()
        sources = source_repo.list_all()
        tasks = task_repo.list_all()

        return {
            "version": __version__,
            "database": "ok",
            "total_articles": total_articles,
            "total_sources": len(sources),
            "enabled_sources": len([s for s in sources if s.enabled]),
            "total_tasks": len(tasks),
            "active_tasks": len([t for t in tasks if t.enabled]),
            "categories": source_repo.get_categories(),
        }
    except Exception as e:
        return {
            "version": __version__,
            "database": "error",
            "error": str(e),
        }
    finally:
        session.close()


@router.get("/system/trending")
async def trending_topics(
    hours: int = 24,
    language: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Get trending topics from recent articles."""
    session = get_session()
    try:
        repo = ArticleRepository(session)
        return repo.get_trending_keywords(hours=hours, language=language, limit=limit)
    finally:
        session.close()
