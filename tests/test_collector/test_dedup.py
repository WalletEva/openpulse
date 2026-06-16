"""Tests for the dedup module."""

from openpulse.collector.base import Article
from openpulse.collector.dedup import DeduplicationFilter, deduplicate_articles


def test_deduplicate_by_url():
    """Test that articles with same source+URL are deduplicated."""
    articles = [
        Article(title="Article 1", source="reuters", url="https://reuters.com/1"),
        Article(title="Article 1 Copy", source="reuters", url="https://reuters.com/1"),
        Article(title="Article 2", source="reuters", url="https://reuters.com/2"),
    ]
    result = deduplicate_articles(articles)
    assert len(result) == 2


def test_deduplicate_with_existing_ids():
    """Test filtering against existing article IDs."""
    existing = {"abc123"}
    articles = [
        Article(id="abc123", title="Existing", source="test"),
        Article(id="new456", title="New", source="test"),
    ]
    result = deduplicate_articles(articles, existing)
    assert len(result) == 1
    assert result[0].id == "new456"


def test_dedup_filter_stateful():
    """Test the stateful DeduplicationFilter."""
    filter = DeduplicationFilter()

    batch1 = [
        Article(title="A1", source="s1", url="u1"),
        Article(title="A2", source="s1", url="u2"),
    ]
    result1 = filter.filter(batch1)
    assert len(result1) == 2
    assert filter.seen_count == 2

    batch2 = [
        Article(title="A1 Again", source="s1", url="u1"),  # duplicate
        Article(title="A3", source="s1", url="u3"),  # new
    ]
    result2 = filter.filter(batch2)
    assert len(result2) == 1
    assert result2[0].title == "A3"
    assert filter.seen_count == 3


def test_dedup_filter_reset():
    """Test resetting the dedup filter."""
    filter = DeduplicationFilter()
    filter.filter([Article(title="A", source="s", url="u")])
    assert filter.seen_count == 1

    filter.reset()
    assert filter.seen_count == 0
