"""Custom RSS feed collector adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import feedparser
import httpx

from ..base import Article, BaseCollector, CollectResult


class CustomRSSCollector(BaseCollector):
    """
    Collector for arbitrary RSS/Atom feeds.

    Use this adapter when a website provides a direct RSS/Atom feed URL
    that doesn't need RSSHub routing.
    """

    @property
    def adapter_name(self) -> str:
        return "custom_rss"

    @property
    def supported_source_types(self) -> list[str]:
        return ["rss", "atom", "custom"]

    async def collect(self, source_config: dict[str, Any]) -> CollectResult:
        """
        Collect articles from a direct RSS/Atom feed URL.

        source_config keys:
            url (str): Direct feed URL
            limit (int, optional): Max articles to return (default 50)
            source_name (str, optional): Human-readable source name
        """
        feed_url = source_config.get("url", "")
        if not feed_url:
            return CollectResult(
                source=source_config.get("source_name", "unknown"),
                adapter=self.adapter_name,
                success=False,
                error="No URL specified in source_config",
            )

        limit = source_config.get("limit", 50)
        source_name = source_config.get("source_name", feed_url)

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(feed_url)
                response.raise_for_status()

            feed = feedparser.parse(response.text)

            articles: list[Article] = []
            for entry in feed.entries[:limit]:
                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6])

                content = ""
                if hasattr(entry, "content") and entry.content:
                    content = entry.content[0].get("value", "")
                elif hasattr(entry, "summary"):
                    content = entry.summary or ""

                tags = []
                if hasattr(entry, "tags"):
                    tags = [t.get("term", "") for t in entry.tags if t.get("term")]

                article = Article(
                    title=entry.get("title", ""),
                    content=content,
                    summary=content[:500] if content else "",
                    source=source_name,
                    source_type="rss",
                    url=entry.get("link", ""),
                    author=entry.get("author", ""),
                    published_at=published_at,
                    language="auto",
                    tags=tags,
                    raw_data={
                        "feed_url": feed_url,
                        "feed_title": feed.feed.get("title", ""),
                    },
                )
                articles.append(article)

            return CollectResult(
                source=source_name,
                adapter=self.adapter_name,
                articles=articles,
                success=True,
                stats={
                    "total_in_feed": len(feed.entries),
                    "collected": len(articles),
                    "limit": limit,
                },
            )

        except httpx.HTTPStatusError as e:
            return CollectResult(
                source=source_name,
                adapter=self.adapter_name,
                success=False,
                error=f"HTTP error {e.response.status_code}: {e.response.text[:200]}",
            )
        except httpx.RequestError as e:
            return CollectResult(
                source=source_name,
                adapter=self.adapter_name,
                success=False,
                error=f"Request error: {str(e)}",
            )
        except Exception as e:
            return CollectResult(
                source=source_name,
                adapter=self.adapter_name,
                success=False,
                error=f"Unexpected error: {str(e)}",
            )
