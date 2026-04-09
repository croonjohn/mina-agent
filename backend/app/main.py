"""Mina Agent — Verse8 Community Manager API."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base
from app.api.v1 import pipeline, content, publish, trends, devvit, promote, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title="Mina Agent API",
    description="Verse8 Community Manager — Reddit/itch.io automation agent",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# CORS for admin dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(publish.router, prefix="/api/v1")
app.include_router(trends.router, prefix="/api/v1")
app.include_router(devvit.router, prefix="/api/v1")
app.include_router(promote.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": settings.app_name, "status": "running", "docs": "/docs"}


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "mina-agent"}
