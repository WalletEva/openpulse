"""Keyword extractor - basic keyword and topic extraction."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


# Common stop words to filter out
STOP_WORDS_EN = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "this", "that", "these",
    "those", "it", "its", "not", "no", "as", "if", "so", "than", "then",
    "also", "just", "more", "most", "very", "too", "only", "about", "up",
    "out", "all", "into", "over", "after", "before", "between", "new",
})

STOP_WORDS_ZH = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "为", "对", "与", "及", "等", "而", "被", "从", "以", "之", "所",
    "可以", "能", "把", "让", "用", "但", "又", "还", "或", "更", "已",
})


def extract_keywords(
    text: str,
    top_n: int = 20,
    min_length: int = 2,
    language: str = "auto",
) -> list[dict[str, Any]]:
    """
    Extract top keywords from text using simple frequency analysis.

    Args:
        text: Input text (plain text or HTML-stripped).
        top_n: Number of top keywords to return.
        min_length: Minimum word length to consider.
        language: 'en', 'zh', or 'auto'.

    Returns:
        List of dicts with 'keyword' and 'count' keys.
    """
    if not text:
        return []

    # Determine which stop words to use
    stop_words: set[str] = set()
    if language in ("en", "auto"):
        stop_words.update(STOP_WORDS_EN)
    if language in ("zh", "auto"):
        stop_words.update(STOP_WORDS_ZH)

    # Extract words
    words: list[str] = []

    # English words
    en_words = re.findall(r"[a-zA-Z]{2,}", text.lower())
    words.extend([w for w in en_words if w not in STOP_WORDS_EN and len(w) >= min_length])

    # Chinese character sequences (simple approach: 2-4 char phrases)
    if language in ("zh", "auto"):
        zh_phrases = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
        words.extend([p for p in zh_phrases if p not in STOP_WORDS_ZH and len(p) >= min_length])

    # Count frequencies
    counter = Counter(words)

    return [
        {"keyword": word, "count": count}
        for word, count in counter.most_common(top_n)
    ]


def extract_topics_from_articles(
    articles: list[Any],
    top_n: int = 20,
) -> list[dict[str, Any]]:
    """
    Extract trending topics from a list of articles.

    Combines titles and tags from all articles to find common topics.

    Args:
        articles: List of article objects (ORM or Pydantic).
        top_n: Number of top topics to return.

    Returns:
        List of dicts with 'keyword', 'count', and 'articles' keys.
    """
    keyword_articles: dict[str, list[str]] = {}

    for article in articles:
        title = getattr(article, "title", "")
        tags = getattr(article, "tags", []) or []
        article_id = getattr(article, "id", "")

        # Process tags directly
        for tag in tags:
            tag_lower = tag.lower().strip()
            if tag_lower and len(tag_lower) >= 2:
                if tag_lower not in keyword_articles:
                    keyword_articles[tag_lower] = []
                keyword_articles[tag_lower].append(article_id)

        # Extract keywords from title
        title_keywords = extract_keywords(title, top_n=5)
        for kw_info in title_keywords:
            kw = kw_info["keyword"]
            if kw not in keyword_articles:
                keyword_articles[kw] = []
            keyword_articles[kw].append(article_id)

    # Sort by number of articles mentioning the keyword
    sorted_topics = sorted(
        keyword_articles.items(),
        key=lambda x: len(set(x[1])),
        reverse=True,
    )

    return [
        {"keyword": kw, "count": len(set(ids)), "articles": len(set(ids))}
        for kw, ids in sorted_topics[:top_n]
    ]
