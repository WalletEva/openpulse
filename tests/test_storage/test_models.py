"""Tests for the storage layer."""

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openpulse.storage.models import Article, Base, Source


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    engine.dispose()
    Path(db_path).unlink(missing_ok=True)


def test_article_creation(temp_db):
    """Test creating and saving an article."""
    article = Article(
        id="test123",
        title="Test Article",
        content="This is test content.",
        source="test-source",
        url="https://example.com/test",
        language="en",
    )
    temp_db.add(article)
    temp_db.commit()

    result = temp_db.query(Article).filter_by(id="test123").first()
    assert result is not None
    assert result.title == "Test Article"
    assert result.source == "test-source"


def test_source_creation(temp_db):
    """Test creating a source configuration."""
    source = Source(
        name="test-rsshub",
        source_type="rsshub",
        adapter="rsshub",
        config={"route": "/reuters/world"},
        category="news",
    )
    temp_db.add(source)
    temp_db.commit()

    result = temp_db.query(Source).filter_by(name="test-rsshub").first()
    assert result is not None
    assert result.adapter == "rsshub"
    assert result.config["route"] == "/reuters/world"


def test_article_search(temp_db):
    """Test searching articles."""
    from openpulse.storage.repositories.article_repo import ArticleRepository

    # Add test articles
    articles = [
        Article(id=f"art{i}", title=f"AI Article {i}", source="tech", language="en", tags=["AI", "tech"])
        for i in range(5)
    ] + [
        Article(id="art-zh", title="人工智能新闻", source="china", language="zh", tags=["AI", "china"]),
    ]
    for a in articles:
        temp_db.add(a)
    temp_db.commit()

    repo = ArticleRepository(temp_db)

    # Search by query
    results = repo.search(query="AI")
    assert len(results) >= 5

    # Search by language
    results = repo.search(language="zh")
    assert len(results) == 1
    assert results[0].title == "人工智能新闻"

    # Count
    total = repo.count()
    assert total == 6
