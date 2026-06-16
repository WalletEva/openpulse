"""SQLAlchemy data models for OpenPulse."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""
    pass


class Source(Base):
    """Configuration for an information source."""

    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True, comment="Human-readable source name")
    source_type = Column(String(50), nullable=False, comment="Source type: rsshub, rss, api, social")
    adapter = Column(String(50), nullable=False, comment="Adapter name: rsshub, custom_rss, newsapi, etc.")
    config = Column(JSON, nullable=False, default=dict, comment="Adapter-specific configuration")
    enabled = Column(Boolean, default=True, nullable=False)
    category = Column(String(100), default="", comment="Source category (news, tech, social, etc.)")
    language = Column(String(10), default="auto", comment="Expected language")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    articles = relationship("Article", back_populates="source_ref", lazy="dynamic")
    tasks = relationship("CollectionTask", back_populates="source_ref", lazy="dynamic")

    __table_args__ = (
        Index("idx_sources_type", "source_type"),
        Index("idx_sources_enabled", "enabled"),
        Index("idx_sources_category", "category"),
    )


class Article(Base):
    """Collected article/item."""

    __tablename__ = "articles"

    id = Column(String(16), primary_key=True, comment="SHA256-based article ID")
    title = Column(String(1000), nullable=False, comment="Article title")
    content = Column(Text, default="", comment="Article content (HTML or plain text)")
    summary = Column(Text, default="", comment="Article summary")
    source = Column(String(200), nullable=False, comment="Source name")
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    source_type = Column(String(50), default="rss", comment="Source type")
    url = Column(String(2000), default="", comment="Original URL")
    author = Column(String(500), default="", comment="Author")
    published_at = Column(DateTime, nullable=True, comment="Publication timestamp")
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="Collection timestamp")
    language = Column(String(10), default="auto", comment="Detected language")
    tags = Column(JSON, default=list, comment="Tags/categories")
    image_url = Column(String(2000), default="", comment="Featured image URL")
    raw_data = Column(JSON, default=dict, comment="Raw source data")

    # Relationships
    source_ref = relationship("Source", back_populates="articles")

    __table_args__ = (
        Index("idx_articles_source", "source"),
        Index("idx_articles_published", "published_at"),
        Index("idx_articles_collected", "collected_at"),
        Index("idx_articles_language", "language"),
        Index("idx_articles_source_type", "source_type"),
    )


class CollectionTask(Base):
    """Scheduled or manual collection task configuration."""

    __tablename__ = "collection_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True, comment="Task name")
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    cron_expr = Column(String(100), nullable=True, comment="Cron expression for scheduled runs")
    enabled = Column(Boolean, default=True, nullable=False)
    max_articles = Column(Integer, default=50, comment="Max articles per run")
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    source_ref = relationship("Source", back_populates="tasks")
    runs = relationship("CollectionRun", back_populates="task", lazy="dynamic")

    __table_args__ = (
        Index("idx_tasks_enabled", "enabled"),
        Index("idx_tasks_next_run", "next_run_at"),
    )


class CollectionRun(Base):
    """Record of a collection task execution."""

    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("collection_tasks.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True, comment="Execution duration")
    articles_collected = Column(Integer, default=0)
    articles_new = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    trigger_type = Column(String(20), default="scheduled", comment="scheduled, manual, event")

    # Relationships
    task = relationship("CollectionTask", back_populates="runs")

    __table_args__ = (
        Index("idx_runs_task", "task_id"),
        Index("idx_runs_started", "started_at"),
        Index("idx_runs_success", "success"),
    )


class Watchlist(Base):
    """Keyword/topic watchlist for monitoring."""

    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(200), nullable=False, unique=True, comment="Keyword or phrase to monitor")
    category = Column(String(100), default="", comment="Watchlist category")
    enabled = Column(Boolean, default=True, nullable=False)
    match_count = Column(Integer, default=0, comment="Number of matching articles found")
    last_matched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_watchlists_enabled", "enabled"),
        Index("idx_watchlists_category", "category"),
    )
