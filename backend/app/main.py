"""Mina Agent — Verse8 Community Manager API."""
import logging
from contextlib import asynccontextmanager
from sqlalchemy import text, inspect
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.auth import APIKeyMiddleware
from app.api.v1 import (
    pipeline,
    content,
    publish,
    trends,
    devvit,
    promote,
    webhooks,
    templates,
    guidelines,
    escalations,
    metrics,
    system,
)
from app.api.v1 import settings as settings_routes


logger = logging.getLogger(__name__)


def _migrate_add_columns(connection):
    """Add new columns to existing tables (SQLite create_all won't alter existing tables)."""
    insp = inspect(connection)
    # content_queue: add source_post_url if missing
    if "content_queue" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("content_queue")]
        if "source_post_url" not in cols:
            connection.execute(text("ALTER TABLE content_queue ADD COLUMN source_post_url TEXT"))
            logger.info("[Migration] Added source_post_url column to content_queue")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_add_columns)
    yield
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title="Mina Agent API",
    description="Verse8 Community Manager — Reddit/itch.io automation agent",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=True,
)

# CORS for admin dashboard (must be before auth middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key auth middleware — enforces key on /api/v1/* except /health and /devvit/*
app.add_middleware(APIKeyMiddleware)

# API routes — existing
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(publish.router, prefix="/api/v1")
app.include_router(trends.router, prefix="/api/v1")
app.include_router(devvit.router, prefix="/api/v1")
app.include_router(promote.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")

# API routes — new
app.include_router(templates.router, prefix="/api/v1")
app.include_router(guidelines.router, prefix="/api/v1")
app.include_router(escalations.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(settings_routes.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}


@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "mina-agent",
        "uptime": "N/A",
        "database": "connected",
    }
