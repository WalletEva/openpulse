"""Scheduler jobs - predefined collection job templates."""

from __future__ import annotations

from typing import Any


def create_rsshub_job(
    name: str,
    route: str,
    cron_expr: str = "*/30 * * * *",
    limit: int = 50,
    base_url: str | None = None,
) -> dict[str, Any]:
    """
    Create a job configuration for an RSSHub source.

    Args:
        name: Job name
        route: RSSHub route (e.g. '/reuters/world')
        cron_expr: Cron expression for scheduling
        limit: Max articles per collection run
        base_url: Custom RSSHub base URL

    Returns:
        Job configuration dict.
    """
    config: dict[str, Any] = {
        "route": route,
        "source_name": name,
        "limit": limit,
    }
    if base_url:
        config["base_url"] = base_url

    return {
        "job_id": f"rsshub:{name}",
        "cron_expr": cron_expr,
        "source_config": config,
        "adapter_name": "rsshub",
    }


def create_rss_job(
    name: str,
    url: str,
    cron_expr: str = "*/30 * * * *",
    limit: int = 50,
) -> dict[str, Any]:
    """
    Create a job configuration for a direct RSS feed.

    Args:
        name: Job name
        url: Direct feed URL
        cron_expr: Cron expression for scheduling
        limit: Max articles per collection run

    Returns:
        Job configuration dict.
    """
    return {
        "job_id": f"rss:{name}",
        "cron_expr": cron_expr,
        "source_config": {
            "url": url,
            "source_name": name,
            "limit": limit,
        },
        "adapter_name": "custom_rss",
    }


# Predefined source templates for common use cases
PREDEFINED_SOURCES: list[dict[str, Any]] = [
    # International News
    create_rsshub_job("reuters-world", "/reuters/world", "*/15 * * * *"),
    create_rsshub_job("bbc-news", "/bbc/zhongwen/simp", "*/30 * * * *"),
    create_rsshub_job("cnn-world", "/cnn/world", "*/30 * * * *"),

    # Chinese Media
    create_rsshub_job("xinhua", "/xinhuanet/fortune", "*/30 * * * *"),
    create_rsshub_job("people-daily", "/people/politics", "*/30 * * * *"),
    create_rsshub_job("36kr", "/36kr/newsflashes", "*/15 * * * *"),
    create_rsshub_job("huxiu", "/huxiu/article", "*/30 * * * *"),

    # Tech
    create_rsshub_job("techcrunch", "/techcrunch", "*/30 * * * *"),
    create_rsshub_job("theverge", "/theverge", "*/30 * * * *"),

    # Social Media
    create_rsshub_job("twitter-trending", "/twitter/trending", "*/10 * * * *"),
    create_rsshub_job("youtube-trending", "/youtube/trending", "*/30 * * * *"),
    create_rsshub_job("weibo-hot", "/weibo/search/hot", "*/10 * * * *"),
    create_rsshub_job("zhihu-hot", "/zhihu/hotlist", "*/15 * * * *"),
]
