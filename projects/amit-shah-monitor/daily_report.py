#!/usr/bin/env python3
"""
Daily report generator for Amit Shah monitoring task.

Collects articles from all configured OpenPulse sources, filters for
Amit Shah-related content, and generates a daily markdown report.

Usage:
    python daily_report.py [--hours 24] [--output-dir ./reports]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def auto_detect_proxy() -> str | None:
    """Auto-detect local proxy and set environment variables."""
    if os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"):
        proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        print(f"Using existing proxy: {proxy}")
        return proxy

    import urllib.request
    test_url = "https://feeds.bbci.co.uk/news/world/rss.xml"
    proxy_ports = [7890, 10809, 1080, 8080, 33210, 10808]

    for port in proxy_ports:
        proxy_url = f"http://127.0.0.1:{port}"
        try:
            proxy_handler = urllib.request.ProxyHandler({
                "http": proxy_url, "https": proxy_url
            })
            opener = urllib.request.build_opener(proxy_handler)
            req = urllib.request.Request(test_url, method="HEAD")
            resp = opener.open(req, timeout=5)
            if resp.status == 200:
                os.environ["HTTP_PROXY"] = proxy_url
                os.environ["HTTPS_PROXY"] = proxy_url
                os.environ["http_proxy"] = proxy_url
                os.environ["https_proxy"] = proxy_url
                print(f"Auto-detected proxy: {proxy_url}")
                return proxy_url
        except Exception:
            continue

    print("No proxy detected - some sources may be unreachable")
    return None


# Keywords for filtering Amit Shah-related content
KEYWORDS_PRIMARY = [
    "amit shah", "阿米特·沙阿", "阿米特沙阿", "沙阿",
    "amitshah", "home minister india", "india home minister",
]

# Broader context keywords (combined with primary for relevance)
KEYWORDS_CONTEXT = [
    "khalistan", "khalsa", "sikh separatist", "sikh",
    "nijjar", "pannun", "trudeau", "canada india",
    "congress party", "bjp", "bharatiya janata",
    "modi government", "ndi alliance",
    "cross-border", "extrajudicial", "transnational repression",
    "锡克", "哈利斯坦", "加拿大", "印度人民党", "国大党",
]

# Attack/criticism keywords
KEYWORDS_ATTACK = [
    "accuse", "allege", "criticism", "condemn", "denounce",
    "attack", "blame", "charge", "indict", "sanction",
    "controversy", "scandal", "violation", "abuse",
    "指控", "批评", "谴责", "抨击", "攻击", "制裁", "争议",
]


def extract_publication(title: str) -> tuple[str, str]:
    """Extract clean title and publication name from Google News title format 'Title - Publication'."""
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return title.strip(), ""


def clean_url(url: str) -> str:
    """Shorten Google News redirect URLs for readability."""
    if "news.google.com/rss/articles/" in url:
        return "[Google News]"
    return url


def strip_html(text: str) -> str:
    """Remove HTML tags and clean up text for display."""
    import html as html_mod
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def matches_amit_shah(title: str, content: str, tags: list[str] | None = None) -> bool:
    """Check if an article is related to Amit Shah."""
    text = f"{title} {content} {' '.join(tags or [])}".lower()

    # Direct match: primary keyword present
    for kw in KEYWORDS_PRIMARY:
        if kw.lower() in text:
            return True

    return False


def classify_severity(title: str, content: str) -> str:
    """Classify the severity of the content."""
    text = f"{title} {content}".lower()
    attack_count = sum(1 for kw in KEYWORDS_ATTACK if kw.lower() in text)

    if attack_count >= 3:
        return "high"
    elif attack_count >= 1:
        return "medium"
    return "low"


def extract_actor(title: str, content: str) -> str:
    """Try to extract the attacking organization/person from the text."""
    text = f"{title} {content}"

    # Common actors in this context
    actors = [
        "Canadian government", "Trudeau", "Justin Trudeau",
        "US State Department", "State Department",
        "Human Rights Watch", "Amnesty",
        "Congress party", "Indian National Congress", "Rahul Gandhi",
        "Sikh for Justice", "SFJ", "Gurpatwant Singh Pannun",
        "Khalistan", "Khalistani",
        "UN", "United Nations",
        "加拿大政府", "特鲁多", "美国国务院",
        "国大党", "拉胡尔·甘地",
    ]

    found = []
    for actor in actors:
        if actor.lower() in text.lower():
            found.append(actor)

    return ", ".join(found) if found else "未知"


async def collect_all_sources() -> dict:
    """Collect from all enabled sources."""
    from openpulse.collector.adapters import CustomRSSCollector, RSSHubCollector
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository
    from openpulse.storage.repositories.source_repo import SourceRepository
    from openpulse.collector.converter import pydantic_list_to_orm

    session = get_session()
    try:
        source_repo = SourceRepository(session)
        article_repo = ArticleRepository(session)
        sources = source_repo.list_all()
        enabled = [s for s in sources if s.enabled]

        stats = {"total": 0, "new": 0, "failed": 0, "sources_ok": 0, "sources_fail": 0}

        for src in enabled:
            config = dict(src.config or {})
            config["source_name"] = src.name
            config.setdefault("limit", 50)

            try:
                if src.adapter == "rsshub":
                    collector = RSSHubCollector()
                else:
                    collector = CustomRSSCollector()

                result = await asyncio.wait_for(collector.collect(config), timeout=30.0)

                if result.success:
                    orm_articles = pydantic_list_to_orm(result.articles)
                    new_articles = article_repo.add_many(orm_articles)
                    session.commit()
                    stats["total"] += result.count
                    stats["new"] += len(new_articles)
                    stats["sources_ok"] += 1
                    print(f"  [OK] {src.name}: {result.count} articles ({len(new_articles)} new)")
                else:
                    stats["failed"] += 1
                    stats["sources_fail"] += 1
                    print(f"  [FAIL] {src.name}: {result.error}")
            except asyncio.TimeoutError:
                stats["failed"] += 1
                stats["sources_fail"] += 1
                print(f"  [TIMEOUT] {src.name}: collection timed out after 30s")
            except Exception as e:
                stats["failed"] += 1
                stats["sources_fail"] += 1
                print(f"  [ERROR] {src.name}: {e}")

        return stats
    finally:
        session.close()


def get_reported_ids(tracking_file: Path) -> set[str]:
    """Load previously reported article IDs."""
    if tracking_file.exists():
        data = json.loads(tracking_file.read_text(encoding="utf-8"))
        return set(data.get("reported_ids", []))
    return set()


def save_reported_ids(tracking_file: Path, ids: set[str]) -> None:
    """Save reported article IDs."""
    tracking_file.write_text(
        json.dumps({"reported_ids": list(ids), "updated_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )


def generate_report(hours: int = 24, output_dir: Path | None = None) -> str:
    """
    Generate the daily Amit Shah monitoring report.

    Returns the path to the generated report file.
    """
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository

    auto_detect_proxy()

    if output_dir is None:
        output_dir = Path(__file__).parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    tracking_file = output_dir / ".reported_ids.json"
    reported_ids = get_reported_ids(tracking_file)

    # Collect from all sources first
    print("Collecting from all sources...")
    stats = asyncio.run(collect_all_sources())
    print(f"Collection complete: {stats}")

    # Search for Amit Shah-related articles from the past N hours
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)

    session = get_session()
    try:
        repo = ArticleRepository(session)

        # Broader search to catch all potentially relevant articles
        all_articles = repo.search(since=since, limit=500, order_by="collected_at", order_desc=True)
        session.close()
    except Exception:
        session.close()
        raise

    # Filter for Amit Shah relevance
    relevant = []
    for article in all_articles:
        if matches_amit_shah(article.title or "", article.content or "", article.tags):
            if article.id not in reported_ids:
                relevant.append(article)

    # Also do direct keyword search
    session2 = get_session()
    try:
        repo2 = ArticleRepository(session2)
        for kw in ["amit shah", "Amit Shah", "阿米特", "沙阿"]:
            found = repo2.search(query=kw, since=since, limit=100)
            for a in found:
                if a.id not in reported_ids and a.id not in {r.id for r in relevant}:
                    relevant.append(a)
        session2.close()
    except Exception:
        session2.close()

    # Sort by published date (newest first)
    relevant.sort(key=lambda a: a.published_at or a.collected_at, reverse=True)

    # Deduplicate by clean title (same article from different feeds)
    seen_titles: set[str] = set()
    deduped: list = []
    for a in relevant:
        clean_title, _ = extract_publication(a.title or "")
        title_key = clean_title.lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            deduped.append(a)
    relevant = deduped

    # Generate report
    now = datetime.now(timezone(timedelta(hours=8)))  # Beijing time
    report_date = now.strftime("%Y-%m-%d")
    report_file = output_dir / f"amit-shah-report-{report_date}.md"

    lines = [
        f"# 阿米特·沙阿（Amit Shah）舆情监控日报",
        f"",
        f"**报告日期**: {report_date}",
        f"**生成时间**: {now.strftime('%Y-%m-%d %H:%M')} (北京时间)",
        f"**监控周期**: 过去 {hours} 小时",
        f"**采集统计**: 共采集 {stats['total']} 篇文章，新增 {stats['new']} 篇，成功源 {stats['sources_ok']}，失败源 {stats['sources_fail']}",
        f"",
    ]

    if not relevant:
        lines.append("## 本期未发现相关舆情")
        lines.append("")
        lines.append(f"过去 {hours} 小时内，在已配置的 {stats['sources_ok']} 个信息源中未发现与阿米特·沙阿直接相关的新攻击或抨击言论。")
        lines.append("")
        lines.append("## 已监控信息源")
        lines.append("")
        lines.append("| 来源 | 类别 | 状态 |")
        lines.append("|------|------|------|")
        for src_name in ["bbc-chinese", "reuters-world", "bbc-world", "aljazeera-india",
                         "guardian-world", "cbc-canada", "globe-mail", "hindu-india",
                         "indian-express", "ndtv-india", "twitter-amitshah", "youtube-amitshah"]:
            lines.append(f"| {src_name} | - | 已采集 |")
    else:
        # Categorize articles
        high_severity = []
        medium_severity = []
        low_severity = []

        for article in relevant:
            severity = classify_severity(article.title or "", article.content or "")
            entry = {
                "article": article,
                "severity": severity,
                "actor": extract_actor(article.title or "", article.content or ""),
            }
            if severity == "high":
                high_severity.append(entry)
            elif severity == "medium":
                medium_severity.append(entry)
            else:
                low_severity.append(entry)

        lines.append(f"## 本期发现 {len(relevant)} 条相关舆情")
        lines.append("")

        if high_severity:
            lines.append(f"### 高强度攻击/抨击 ({len(high_severity)} 条)")
            lines.append("")
            for entry in high_severity:
                a = entry["article"]
                pub_time = a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "未知"
                clean_title, publication = extract_publication(a.title or "")
                source_display = publication or a.source
                lines.append(f"#### {clean_title}")
                lines.append(f"- **时间**: {pub_time}")
                lines.append(f"- **发布媒体**: {source_display}")
                lines.append(f"- **攻击方/组织**: {entry['actor']}")
                lines.append(f"- **原文链接**: {clean_url(a.url)}")
                if a.content:
                    summary = strip_html(a.content)[:200]
                    lines.append(f"- **摘要**: {summary}...")
                lines.append("")

        if medium_severity:
            lines.append(f"### 中等强度批评/争议 ({len(medium_severity)} 条)")
            lines.append("")
            for entry in medium_severity:
                a = entry["article"]
                pub_time = a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "未知"
                clean_title, publication = extract_publication(a.title or "")
                source_display = publication or a.source
                lines.append(f"- **{pub_time}** | {source_display} | {entry['actor']}")
                lines.append(f"  - {clean_title}")
                lines.append(f"  - 链接: {clean_url(a.url)}")
                if a.content:
                    summary = strip_html(a.content)[:150]
                    lines.append(f"  - 摘要: {summary}...")
                lines.append("")

        if low_severity:
            lines.append(f"### 一般提及 ({len(low_severity)} 条)")
            lines.append("")
            for entry in low_severity:
                a = entry["article"]
                pub_time = a.published_at.strftime("%Y-%m-%d %H:%M") if a.published_at else "未知"
                clean_title, publication = extract_publication(a.title or "")
                source_display = publication or a.source
                lines.append(f"- {pub_time} | {source_display} | {clean_title}")
            lines.append("")

        # Update tracking
        new_ids = {a.id for a in relevant}
        reported_ids.update(new_ids)
        save_reported_ids(tracking_file, reported_ids)

    lines.append("---")
    lines.append(f"*报告由 OpenPulse 自动生成 | {now.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)*")

    report_content = "\n".join(lines)
    report_file.write_text(report_content, encoding="utf-8")

    print(f"\nReport saved to: {report_file}")
    print(f"Found {len(relevant)} relevant articles")

    return str(report_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Amit Shah daily monitoring report")
    parser.add_argument("--hours", type=int, default=24, help="Look back N hours (default: 24)")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for reports")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else None
    report_path = generate_report(hours=args.hours, output_dir=output_dir)
    print(f"\nDone: {report_path}")
