"""Base collector interface and data structures."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Article(BaseModel):
    """Standardized article model."""

    id: str = Field(default="", description="Unique article ID (auto-generated hash)")
    title: str = Field(description="Article title")
    content: str = Field(default="", description="Article content (plain text or HTML)")
    summary: str = Field(default="", description="Article summary")
    source: str = Field(description="Source name/identifier")
    source_type: str = Field(default="rss", description="Source type (rss, api, social)")
    url: str = Field(default="", description="Original article URL")
    author: str = Field(default="", description="Article author")
    published_at: datetime | None = Field(default=None, description="Publication timestamp")
    collected_at: datetime = Field(default_factory=datetime.utcnow, description="Collection timestamp")
    language: str = Field(default="auto", description="Article language code")
    tags: list[str] = Field(default_factory=list, description="Article tags/categories")
    image_url: str = Field(default="", description="Featured image URL")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw source data")

    def model_post_init(self, __context: Any) -> None:
        """Auto-generate ID from title + url if not provided."""
        if not self.id:
            key = f"{self.source}:{self.url or self.title}"
            self.id = hashlib.sha256(key.encode()).hexdigest()[:16]


class CollectResult(BaseModel):
    """Result of a collection operation."""

    source: str
    adapter: str
    articles: list[Article] = Field(default_factory=list)
    success: bool = True
    error: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.articles)


class BaseCollector(ABC):
    """Abstract base class for all collectors."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Unique identifier for this adapter."""
        ...

    @property
    @abstractmethod
    def supported_source_types(self) -> list[str]:
        """List of source types this adapter can handle."""
        ...

    @abstractmethod
    async def collect(self, source_config: dict[str, Any]) -> CollectResult:
        """
        Collect articles from the specified source.

        Args:
            source_config: Configuration dict containing source-specific parameters
                          (URL, route, API key, etc.)

        Returns:
            CollectResult with collected articles and metadata.
        """
        ...

    async def validate_source(self, source_config: dict[str, Any]) -> bool:
        """
        Validate that a source configuration is usable.

        Returns True if the source is reachable and valid.
        """
        try:
            result = await self.collect(source_config)
            return result.success
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} adapter={self.adapter_name}>"
