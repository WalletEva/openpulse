"""Article repository - CRUD operations for articles."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Article


class ArticleRepository:
    """Repository for article data access."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, article: Article) -> Article:
        """Add a new article to the database."""
        self.session.add(article)
        self.session.flush()
        return article

    def add_many(self, articles: list[Article]) -> list[Article]:
        """Add multiple articles, skipping duplicates."""
        added: list[Article] = []
        for article in articles:
            existing = self.get_by_id(article.id)
            if not existing:
                self.session.add(article)
                added.append(article)
        self.session.flush()
        return added

    def get_by_id(self, article_id: str) -> Article | None:
        """Get an article by its ID."""
        stmt = select(Article).where(Article.id == article_id)
        return self.session.scalars(stmt).first()

    def search(
        self,
        query: str | None = None,
        source: str | None = None,
        source_type: str | None = None,
        language: str | None = None,
        tags: list[str] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "collected_at",
        order_desc: bool = True,
    ) -> list[Article]:
        """
        Search articles with various filters.

        Args:
            query: Full-text search in title and content
            source: Filter by source name
            source_type: Filter by source type
            language: Filter by language
            tags: Filter by tags (any match)
            since: Only articles published after this date
            until: Only articles published before this date
            limit: Max results to return
            offset: Pagination offset
            order_by: Column to order by
            order_desc: Descending order
        """
        stmt = select(Article)

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                Article.title.ilike(pattern) | Article.content.ilike(pattern)
            )

        if source:
            stmt = stmt.where(Article.source == source)

        if source_type:
            stmt = stmt.where(Article.source_type == source_type)

        if language and language != "auto":
            stmt = stmt.where(Article.language == language)

        if tags:
            # JSON array contains any of the tags
            for tag in tags:
                stmt = stmt.where(Article.tags.contains(tag))

        if since:
            stmt = stmt.where(Article.published_at >= since)

        if until:
            stmt = stmt.where(Article.published_at <= until)

        # Ordering
        order_col = getattr(Article, order_by, Article.collected_at)
        stmt = stmt.order_by(order_col.desc() if order_desc else order_col.asc())

        stmt = stmt.offset(offset).limit(limit)

        return list(self.session.scalars(stmt).all())

    def count(
        self,
        source: str | None = None,
        source_type: str | None = None,
        language: str | None = None,
    ) -> int:
        """Count articles matching filters."""
        stmt = select(func.count(Article.id))

        if source:
            stmt = stmt.where(Article.source == source)
        if source_type:
            stmt = stmt.where(Article.source_type == source_type)
        if language and language != "auto":
            stmt = stmt.where(Article.language == language)

        return self.session.scalar(stmt) or 0

    def get_existing_ids(self) -> set[str]:
        """Get all existing article IDs (for deduplication)."""
        stmt = select(Article.id)
        return {row[0] for row in self.session.execute(stmt).all()}

    def get_trending_keywords(
        self,
        hours: int = 24,
        language: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get trending keywords from recent articles.

        This is a simple tag frequency analysis.
        A more sophisticated implementation would use NLP.
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = select(Article).where(Article.collected_at >= since)

        if language and language != "auto":
            stmt = stmt.where(Article.language == language)

        articles = list(self.session.scalars(stmt).all())

        # Count tag frequencies
        tag_counts: dict[str, int] = {}
        for article in articles:
            for tag in (article.tags or []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by frequency
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        return [
            {"keyword": tag, "count": count, "period_hours": hours}
            for tag, count in sorted_tags[:limit]
        ]

    def delete_old(self, days: int = 30) -> int:
        """Delete articles older than specified days. Returns count of deleted articles."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = select(Article).where(Article.collected_at < cutoff)
        old_articles = list(self.session.scalars(stmt).all())
        count = len(old_articles)
        for article in old_articles:
            self.session.delete(article)
        self.session.flush()
        return count
