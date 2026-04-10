"""Metrics API endpoints — aggregate stats from existing tables."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.core.database import get_db
from app.models.models import (
    PipelineRun,
    ScrapedPost,
    ContentItem,
    PublishedPost,
    Escalation,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _period_start(period: str) -> datetime:
    """Return the start datetime for the given period."""
    now = datetime.now(timezone.utc)
    if period == "daily":
        return now - timedelta(days=1)
    elif period == "weekly":
        return now - timedelta(weeks=1)
    elif period == "monthly":
        return now - timedelta(days=30)
    else:
        raise HTTPException(status_code=400, detail="Invalid period. Use daily, weekly, or monthly.")


@router.get("/summary")
async def get_metrics_summary(
    period: str = "weekly",
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregate stats for the given period.

    - **period**: daily, weekly, or monthly
    """
    since = _period_start(period)

    # Pipeline runs
    pipeline_result = await db.execute(
        select(
            func.count(PipelineRun.id).label("total_runs"),
            func.sum(PipelineRun.posts_scraped).label("total_scraped"),
            func.sum(PipelineRun.contents_generated).label("total_generated"),
            func.sum(PipelineRun.contents_published).label("total_published"),
        ).where(PipelineRun.started_at >= since)
    )
    pipeline_row = pipeline_result.one()

    # Content items by status
    content_result = await db.execute(
        select(
            ContentItem.status,
            func.count(ContentItem.id).label("count"),
        )
        .where(ContentItem.created_at >= since)
        .group_by(ContentItem.status)
    )
    content_by_status = {row.status: row.count for row in content_result.all()}

    # Published posts performance
    published_result = await db.execute(
        select(
            func.count(PublishedPost.id).label("count"),
            func.coalesce(func.avg(PublishedPost.score), 0).label("avg_score"),
            func.coalesce(func.avg(PublishedPost.comment_count), 0).label("avg_comments"),
            func.coalesce(func.sum(PublishedPost.score), 0).label("total_score"),
        ).where(PublishedPost.published_at >= since)
    )
    published_row = published_result.one()

    # Escalations
    escalation_result = await db.execute(
        select(
            func.count(Escalation.id).label("total"),
        ).where(Escalation.created_at >= since)
    )
    escalation_total = escalation_result.scalar() or 0

    open_escalations_result = await db.execute(
        select(func.count(Escalation.id)).where(Escalation.status == "open")
    )
    open_escalations = open_escalations_result.scalar() or 0

    return {
        "period": period,
        "since": since.isoformat(),
        "pipelines": {
            "total_runs": pipeline_row.total_runs or 0,
            "total_scraped": pipeline_row.total_scraped or 0,
            "total_generated": pipeline_row.total_generated or 0,
            "total_published": pipeline_row.total_published or 0,
        },
        "content": {
            "by_status": content_by_status,
            "total": sum(content_by_status.values()) if content_by_status else 0,
        },
        "published": {
            "count": published_row.count or 0,
            "avg_score": round(float(published_row.avg_score), 1),
            "avg_comments": round(float(published_row.avg_comments), 1),
            "total_score": int(published_row.total_score),
        },
        "escalations": {
            "total_in_period": escalation_total,
            "currently_open": open_escalations,
        },
    }


@router.get("/subreddits")
async def get_subreddit_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Per-subreddit performance metrics from scraped and published data."""
    # Scraped post counts by source (subreddit)
    scraped_result = await db.execute(
        select(
            ScrapedPost.source,
            func.count(ScrapedPost.id).label("posts_scraped"),
            func.coalesce(func.avg(ScrapedPost.score), 0).label("avg_score"),
            func.coalesce(func.avg(ScrapedPost.comment_count), 0).label("avg_comments"),
        )
        .where(ScrapedPost.platform == "reddit")
        .group_by(ScrapedPost.source)
        .order_by(func.count(ScrapedPost.id).desc())
    )
    scraped_rows = scraped_result.all()

    # Content generated per target
    content_result = await db.execute(
        select(
            ContentItem.target,
            func.count(ContentItem.id).label("content_count"),
        )
        .where(ContentItem.platform == "reddit")
        .group_by(ContentItem.target)
    )
    content_by_target = {row.target: row.content_count for row in content_result.all()}

    subreddits = []
    for row in scraped_rows:
        subreddits.append({
            "subreddit": row.source,
            "posts_scraped": row.posts_scraped,
            "avg_score": round(float(row.avg_score), 1),
            "avg_comments": round(float(row.avg_comments), 1),
            "content_generated": content_by_target.get(row.source, 0),
        })

    return {"subreddits": subreddits}
