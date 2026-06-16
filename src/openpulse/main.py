"""FastAPI application entry point for OpenPulse."""

from __future__ import annotations

from fastapi import FastAPI

from openpulse import __version__

app = FastAPI(
    title="OpenPulse API",
    description="Open-source intelligence gathering and aggregation platform",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
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
    return {"status": "healthy", "version": __version__}


# TODO: Mount REST API routers in Phase 2
# from openpulse.api.rest import articles, sources, tasks, watchlists, system
# app.include_router(articles.router, prefix="/api/v1")
# app.include_router(sources.router, prefix="/api/v1")
# app.include_router(tasks.router, prefix="/api/v1")
# app.include_router(watchlists.router, prefix="/api/v1")
# app.include_router(system.router, prefix="/api/v1")
