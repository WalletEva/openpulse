"""Tests for the collector module."""

import pytest

from openpulse.collector.base import Article, CollectResult


def test_article_auto_id():
    """Test that article ID is auto-generated from source + URL."""
    article = Article(
        title="Test Article",
        source="reuters",
        url="https://reuters.com/test-article",
    )
    assert article.id != ""
    assert len(article.id) == 16

    # Same source + URL should produce same ID
    article2 = Article(
        title="Different Title",
        source="reuters",
        url="https://reuters.com/test-article",
    )
    assert article.id == article2.id


def test_article_different_ids():
    """Test that different articles get different IDs."""
    a1 = Article(title="Article 1", source="reuters", url="https://reuters.com/1")
    a2 = Article(title="Article 2", source="reuters", url="https://reuters.com/2")
    assert a1.id != a2.id


def test_collect_result():
    """Test CollectResult model."""
    articles = [
        Article(title=f"Article {i}", source="test")
        for i in range(5)
    ]
    result = CollectResult(
        source="test",
        adapter="rsshub",
        articles=articles,
        success=True,
    )
    assert result.count == 5
    assert result.success is True
    assert result.error is None


def test_collect_result_error():
    """Test CollectResult with error."""
    result = CollectResult(
        source="test",
        adapter="rsshub",
        success=False,
        error="Connection timeout",
    )
    assert result.count == 0
    assert result.success is False
    assert "timeout" in result.error.lower()
