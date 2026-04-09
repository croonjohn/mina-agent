"""Pipeline API endpoints."""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.models import PipelineRun
from app.services.pipeline import run_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class PipelineRunRequest(BaseModel):
    platforms: list[str] = ["reddit", "itchio"]
    tiers: list[int] = [1, 2]
    content_types: list[str] = ["post", "comment"]
    auto_approve: bool = False


class PipelineResponse(BaseModel):
    pipeline_id: str
    status: str
    message: str = ""


# In-memory store for background pipeline results
_pipeline_results: dict = {}


async def _run_pipeline_background(
    pipeline_id: str,
    request: PipelineRunRequest,
    db: AsyncSession,
):
    result = await run_pipeline(
        db=db,
        platforms=request.platforms,
        tiers=request.tiers,
        content_types=request.content_types,
        auto_approve=request.auto_approve,
    )
    _pipeline_results[pipeline_id] = result


@router.post("/run", response_model=PipelineResponse)
async def run_full_pipeline(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Run the full pipeline: scrape → analyze → generate."""
    result = await run_pipeline(
        db=db,
        platforms=request.platforms,
        tiers=request.tiers,
        content_types=request.content_types,
        auto_approve=request.auto_approve,
    )
    return PipelineResponse(
        pipeline_id=result["pipeline_id"],
        status=result["status"],
        message=f"Scraped {result.get('posts_scraped', 0)} posts, generated {result.get('contents_generated', 0)} content items.",
    )


@router.post("/run/scrape-only")
async def run_scrape_only(
    request: PipelineRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run scraping step only."""
    from app.scrapers.reddit_scraper import scrape_tiers
    from app.scrapers.itchio_scraper import scrape_all_itchio
    from app.models.models import ScrapedPost, PipelineRun
    from datetime import datetime, timezone
    import uuid

    pipeline = PipelineRun(config={"mode": "scrape-only"}, status="running")
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)

    all_posts = []
    if "reddit" in request.platforms:
        all_posts.extend(await scrape_tiers(tiers=request.tiers))
    if "itchio" in request.platforms:
        all_posts.extend(await scrape_all_itchio())

    for p in all_posts:
        db.add(ScrapedPost(
            pipeline_id=pipeline.id,
            platform=p["platform"], source=p["source"],
            external_id=p["external_id"], title=p["title"],
            body=p.get("body"), author=p.get("author"),
            url=p.get("url"), score=p.get("score", 0),
            comment_count=p.get("comment_count", 0),
            metadata_=p.get("metadata", {}),
        ))

    pipeline.status = "completed"
    pipeline.posts_scraped = len(all_posts)
    pipeline.completed_at = datetime.now(timezone.utc)
    await db.commit()

    return {"pipeline_id": str(pipeline.id), "status": "completed", "posts_scraped": len(all_posts)}


@router.get("/status/{pipeline_id}")
async def get_pipeline_status(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    """Get pipeline run status."""
    from uuid import UUID
    result = await db.execute(
        select(PipelineRun).where(PipelineRun.id == UUID(pipeline_id))
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return {"error": "Pipeline not found"}

    return {
        "pipeline_id": str(pipeline.id),
        "status": pipeline.status,
        "steps": pipeline.steps,
        "posts_scraped": pipeline.posts_scraped,
        "contents_generated": pipeline.contents_generated,
        "contents_published": pipeline.contents_published,
        "started_at": pipeline.started_at.isoformat() if pipeline.started_at else None,
        "completed_at": pipeline.completed_at.isoformat() if pipeline.completed_at else None,
        "error": pipeline.error,
    }


@router.get("/history")
async def get_pipeline_history(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Get pipeline run history."""
    result = await db.execute(
        select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)
    )
    runs = result.scalars().all()
    return [
        {
            "pipeline_id": str(r.id),
            "status": r.status,
            "posts_scraped": r.posts_scraped,
            "contents_generated": r.contents_generated,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]
