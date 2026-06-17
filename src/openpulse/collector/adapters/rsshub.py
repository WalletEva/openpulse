"""RSSHub adapter - integrates with self-hosted or public RSSHub instances."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import feedparser
import httpx

from ..base import Article, BaseCollector, CollectResult


class RSSHubCollector(BaseCollector):
    """
    Collector adapter for RSSHub.

    RSSHub generates RSS feeds for hundreds of websites including:
    - X/Twitter, YouTube, Reddit, Telegram (social media)
    - Reuters, BBC, CNN, Bloomberg (international news)
    - 新华社, 人民网, 央视新闻, 36氪 (Chinese media)

    See https://docs.rsshub.app/ for available routes.
    """

    @property
    def adapter_name(self) -> str:
        return "rsshub"

    @property
    def supported_source_types(self) -> list[str]:
        return ["rsshub", "rss"]

    def _build_url(self, route: str, base_url: str | None = None) -> str:
        """Build the full RSSHub URL for a given route."""
        base = base_url or self.config.get("base_url", "http://localhost:1200")
        base = base.rstrip("/")
        route = route.lstrip("/")
        return f"{base}/{route}"

    async def collect(self, source_config: dict[str, Any]) -> CollectResult:
        """
        Collect articles from an RSSHub route.

        source_config keys:
            route (str): RSSHub route, e.g. "/reuters/world" or "/twitter/trending"
            base_url (str, optional): Custom RSSHub base URL
            limit (int, optional): Max articles to return (default 50)
            source_name (str, optional): Human-readable source name
        """
        route = source_config.get("route", "")
        if not route:
            return CollectResult(
                source=source_config.get("source_name", "unknown"),
                adapter=self.adapter_name,
                success=False,
                error="No route specified in source_config",
            )

        base_url = source_config.get("base_url")
        limit = source_config.get("limit", 50)
        source_name = source_config.get("source_name", route)

        url = self._build_url(route, base_url)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
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

                image_url = ""
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url", "")
                elif hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get("url", "")

                tags = []
                if hasattr(entry, "tags"):
                    tags = [t.get("term", "") for t in entry.tags if t.get("term")]

                article = Article(
                    title=entry.get("title", ""),
                    content=content,
                    summary=content[:500] if content else "",
                    source=source_name,
                    source_type="rsshub",
                    url=entry.get("link", ""),
                    author=entry.get("author", ""),
                    published_at=published_at,
                    language="auto",
                    tags=tags,
                    image_url=image_url,
                    raw_data={
                        "rsshub_route": route,
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
