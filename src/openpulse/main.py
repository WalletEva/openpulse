"""FastAPI application entry point for OpenPulse."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from openpulse import __version__

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler - runs on startup and shutdown."""
    # Startup: initialize database and scheduler
    from openpulse.storage.database import get_engine, init_db

    engine = get_engine()
    init_db(engine)
    logger.info("Database initialized")

    # Start scheduler if enabled
    from openpulse.config import load_settings

    settings = load_settings()
    if settings.scheduler_enabled:
        from openpulse.scheduler.engine import SchedulerEngine

        app.state.scheduler = SchedulerEngine(
            max_instances=settings.scheduler_max_instances
        )
        app.state.scheduler.start()
        logger.info("Scheduler started")
    else:
        app.state.scheduler = None

    yield

    # Shutdown: stop scheduler
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler and scheduler.is_running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


app = FastAPI(
    title="OpenPulse API",
    description="Open-source intelligence gathering and aggregation platform",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict:
    """Root endpoint - API information."""
    return {
        "name": "OpenPulse",
        "version": __version__,
        "description": "Open-source intelligence gathering and aggregation platform",
        "docs": "/api/docs",
        "health": "/api/v1/health",
    }


@app.get("/api/v1/health")
async def health_check() -> dict:
    """Health check endpoint."""
    from openpulse.storage.database import get_session
    from openpulse.storage.repositories.article_repo import ArticleRepository

    db_ok = True
    article_count = 0
    try:
        session = get_session()
        repo = ArticleRepository(session)
        article_count = repo.count()
        session.close()
    except Exception:
        db_ok = False

    scheduler = getattr(app.state, "scheduler", None)
    scheduler_running = scheduler.is_running if scheduler else False

    return {
        "status": "healthy" if db_ok else "degraded",
        "version": __version__,
        "database": "ok" if db_ok else "error",
        "articles_count": article_count,
        "scheduler": "running" if scheduler_running else "stopped",
    }


# Mount REST API routers
from openpulse.api.rest import articles, sources, tasks, watchlists, system  # noqa: E402

app.include_router(articles.router, prefix="/api/v1")
app.include_router(sources.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(watchlists.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
