"""Article deduplication module."""

from __future__ import annotations

import hashlib
from typing import Iterable

from .base import Article


def compute_article_hash(article: Article) -> str:
    """Compute a deterministic hash for an article based on source + url or title."""
    key = f"{article.source}:{article.url or article.title}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def deduplicate_articles(
    articles: Iterable[Article],
    existing_ids: set[str] | None = None,
) -> list[Article]:
    """
    Remove duplicate articles from a collection.

    Deduplication is based on article ID (derived from source + URL).
    If existing_ids is provided, also filters out articles that already exist.

    Args:
        articles: Iterable of articles to deduplicate.
        existing_ids: Set of already-known article IDs to exclude.

    Returns:
        List of unique articles.
    """
    seen: set[str] = set(existing_ids or [])
    unique: list[Article] = []

    for article in articles:
        aid = article.id or compute_article_hash(article)
        if aid not in seen:
            seen.add(aid)
            if not article.id:
                article.id = aid
            unique.append(article)

    return unique


class DeduplicationFilter:
    """Stateful deduplication filter that tracks seen article IDs across calls."""

    def __init__(self) -> None:
        self._seen_ids: set[str] = set()

    def filter(self, articles: list[Article]) -> list[Article]:
        """Filter articles, keeping only those not seen before."""
        result = deduplicate_articles(articles, self._seen_ids)
        for article in result:
            self._seen_ids.add(article.id)
        return result

    def reset(self) -> None:
        """Clear the seen IDs set."""
        self._seen_ids.clear()

    @property
    def seen_count(self) -> int:
        """Number of unique articles seen so far."""
        return len(self._seen_ids)
