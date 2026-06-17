"""MCP Server module for OpenPulse.

This module exposes OpenPulse as an MCP (Model Context Protocol) server,
allowing AI agents like Hermes and OpenClaw to interact with the platform.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP

from openpulse import __version__

# Create MCP server instance
mcp = FastMCP(
    name="openpulse",
    version=__version__,
    description="OpenPulse - Open-source intelligence gathering platform for AI agents",
)


@mcp.tool()
def search_articles(
    query: str,
    sources: list[str] | None = None,
    language: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Search collected articles by keyword, with optional source and language filters.

    Args:
        query: Search keyword or phrase
        sources: List of source names to filter by (optional)
        language: Language code filter (e.g. 'zh', 'en')
        limit: Maximum number of results (default 20)

    Returns:
        List of matching articles with title, source, URL, date, and summary.
    """
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository

    session = get_session()
    repo = ArticleRepository(session)

    articles = repo.search(
        query=query,
        source=sources[0] if sources and len(sources) == 1 else None,
        language=language,
        limit=limit,
    )
    session.close()

    return [
        {
            "id": a.id,
            "title": a.title,
            "source": a.source,
            "url": a.url,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "language": a.language,
            "tags": a.tags,
            "summary": a.summary[:200] if a.summary else "",
        }
        for a in articles
    ]


@mcp.tool()
def collect_now(
    source_name: str | None = None,
    rsshub_route: str | None = None,
    feed_url: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Trigger an immediate collection run.

    Provide one of: source_name (configured source), rsshub_route, or feed_url.

    Args:
        source_name: Name of a configured source to collect
        rsshub_route: RSSHub route to collect (e.g. '/reuters/world')
        feed_url: Direct RSS/Atom feed URL
        limit: Maximum articles to collect (default 50)

    Returns:
        Collection result with article count and new article list.
    """
    from openpulse.collector.adapters import CustomRSSCollector, RSSHubCollector
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository
    from openpulse.storage.repositories.source_repo import SourceRepository

    async def _collect() -> dict[str, Any]:
        if rsshub_route:
            collector = RSSHubCollector()
            config = {"route": rsshub_route, "limit": limit, "source_name": rsshub_route}
        elif feed_url:
            collector = CustomRSSCollector()
            config = {"url": feed_url, "limit": limit, "source_name": feed_url}
        elif source_name:
            session = get_session()
            repo = SourceRepository(session)
            src = repo.get_by_name(source_name)
            session.close()
            if not src:
                return {"error": f"Source '{source_name}' not found"}
            config = {**(src.config or {}), "source_name": src.name, "limit": limit}
            if src.adapter == "rsshub":
                collector = RSSHubCollector()
            else:
                collector = CustomRSSCollector()
        else:
            return {"error": "Provide source_name, rsshub_route, or feed_url"}

        result = await collector.collect(config)
        if not result.success:
            return {"error": result.error}

        from openpulse.collector.converter import pydantic_list_to_orm
        orm_articles = pydantic_list_to_orm(result.articles)

        session = get_session()
        try:
            article_repo = ArticleRepository(session)
            new_articles = article_repo.add_many(orm_articles)
            session.commit()
        finally:
            session.close()

        return {
            "source": result.source,
            "total_collected": result.count,
            "new_articles": len(new_articles),
            "articles": [
                {"title": a.title, "url": a.url, "published_at": a.published_at.isoformat() if a.published_at else None}
                for a in new_articles[:10]
            ],
        }

    return asyncio.run(_collect())


@mcp.tool()
def get_trending_topics(
    language: str = "auto",
    hours: int = 24,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Get trending topics/keywords from recently collected articles.

    Args:
        language: Language filter ('zh', 'en', 'auto' for all)
        hours: Time window in hours (default 24)
        limit: Max topics to return (default 20)

    Returns:
        List of trending topics with keyword, count, and period.
    """
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository

    session = get_session()
    repo = ArticleRepository(session)
    trending = repo.get_trending_keywords(hours=hours, language=language, limit=limit)
    session.close()

    return trending


@mcp.tool()
def get_article_detail(article_id: str) -> dict[str, Any]:
    """
    Get full details of a specific article by its ID.

    Args:
        article_id: The unique article ID

    Returns:
        Complete article data including full content.
    """
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository

    session = get_session()
    repo = ArticleRepository(session)
    article = repo.get_by_id(article_id)
    session.close()

    if not article:
        return {"error": f"Article '{article_id}' not found"}

    return {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "summary": article.summary,
        "source": article.source,
        "source_type": article.source_type,
        "url": article.url,
        "author": article.author,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "collected_at": article.collected_at.isoformat() if article.collected_at else None,
        "language": article.language,
        "tags": article.tags,
        "image_url": article.image_url,
    }


@mcp.tool()
def get_sources(
    category: str | None = None,
    enabled_only: bool = False,
) -> list[dict[str, Any]]:
    """
    List configured information sources.

    Args:
        category: Filter by category (e.g. 'news', 'tech', 'social')
        enabled_only: Only return enabled sources

    Returns:
        List of source configurations.
    """
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.source_repo import SourceRepository

    session = get_session()
    repo = SourceRepository(session)
    sources = repo.list_all(
        category=category,
        enabled=True if enabled_only else None,
    )
    session.close()

    return [
        {
            "id": s.id,
            "name": s.name,
            "source_type": s.source_type,
            "adapter": s.adapter,
            "category": s.category,
            "enabled": s.enabled,
            "language": s.language,
        }
        for s in sources
    ]


@mcp.tool()
def manage_watchlist(
    action: str,
    keywords: list[str] | None = None,
    category: str = "",
) -> dict[str, Any]:
    """
    Manage the keyword watchlist for monitoring.

    Args:
        action: 'add', 'remove', or 'list'
        keywords: List of keywords (required for add/remove)
        category: Category for the watchlist items

    Returns:
        Operation result with current watchlist state.
    """
    from sqlalchemy import select
    from openpulse.storage.database import get_session
    from openpulse.storage.models import Watchlist

    session = get_session()

    if action == "list":
        stmt = select(Watchlist).order_by(Watchlist.keyword.asc())
        items = list(session.scalars(stmt).all())
        session.close()
        return {
            "watchlist": [
                {
                    "id": w.id,
                    "keyword": w.keyword,
                    "category": w.category,
                    "enabled": w.enabled,
                    "match_count": w.match_count,
                }
                for w in items
            ]
        }

    elif action == "add":
        if not keywords:
            session.close()
            return {"error": "keywords required for 'add' action"}
        added = []
        for kw in keywords:
            existing = session.scalar(
                select(Watchlist).where(Watchlist.keyword == kw)
            )
            if not existing:
                w = Watchlist(keyword=kw, category=category)
                session.add(w)
                added.append(kw)
        session.commit()
        session.close()
        return {"added": added, "total_keywords": len(keywords)}

    elif action == "remove":
        if not keywords:
            session.close()
            return {"error": "keywords required for 'remove' action"}
        removed = []
        for kw in keywords:
            w = session.scalar(
                select(Watchlist).where(Watchlist.keyword == kw)
            )
            if w:
                session.delete(w)
                removed.append(kw)
        session.commit()
        session.close()
        return {"removed": removed}

    else:
        session.close()
        return {"error": f"Unknown action: {action}. Use 'add', 'remove', or 'list'"}


def run_mcp_server() -> None:
    """Run the MCP server (entry point for 'python -m openpulse.mcp_server')."""
    mcp.run()


if __name__ == "__main__":
    run_mcp_server()
