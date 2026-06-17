"""Conversion layer between Pydantic collector models and SQLAlchemy ORM models.

The collector layer produces Pydantic `Article` objects (openpulse.collector.base.Article).
The storage layer uses SQLAlchemy `Article` objects (openpulse.storage.models.Article).
This module provides bidirectional conversion between the two.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openpulse.collector.base import Article as PydanticArticle
    from openpulse.storage.models import Article as ORMArticle


def pydantic_to_orm(article: PydanticArticle) -> ORMArticle:
    """Convert a Pydantic Article (from collector) to a SQLAlchemy Article (for storage).

    Args:
        article: A Pydantic Article instance from the collector layer.

    Returns:
        A SQLAlchemy Article instance ready for database insertion.
    """
    from openpulse.storage.models import Article as ORMArticle

    return ORMArticle(
        id=article.id,
        title=article.title,
        content=article.content,
        summary=article.summary,
        source=article.source,
        source_type=article.source_type,
        url=article.url,
        author=article.author,
        published_at=article.published_at,
        collected_at=article.collected_at,
        language=article.language,
        tags=article.tags,
        image_url=article.image_url,
        raw_data=article.raw_data,
    )


def orm_to_pydantic(article: ORMArticle) -> PydanticArticle:
    """Convert a SQLAlchemy Article (from storage) to a Pydantic Article (for collector/API).

    Args:
        article: A SQLAlchemy Article instance from the database.

    Returns:
        A Pydantic Article instance.
    """
    from openpulse.collector.base import Article as PydanticArticle

    return PydanticArticle(
        id=article.id,
        title=article.title,
        content=article.content or "",
        summary=article.summary or "",
        source=article.source,
        source_type=article.source_type or "rss",
        url=article.url or "",
        author=article.author or "",
        published_at=article.published_at,
        collected_at=article.collected_at,
        language=article.language or "auto",
        tags=article.tags or [],
        image_url=article.image_url or "",
        raw_data=article.raw_data or {},
    )


def pydantic_list_to_orm(articles: list[PydanticArticle]) -> list[ORMArticle]:
    """Convert a list of Pydantic Articles to SQLAlchemy Articles."""
    return [pydantic_to_orm(a) for a in articles]


def orm_list_to_pydantic(articles: list[ORMArticle]) -> list[PydanticArticle]:
    """Convert a list of SQLAlchemy Articles to Pydantic Articles."""
    return [orm_to_pydantic(a) for a in articles]
