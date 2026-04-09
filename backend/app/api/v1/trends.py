"""Trends API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.database import get_db
from app.models.models import TrendAnalysis

router = APIRouter(prefix="/trends", tags=["trends"])


async def _get_latest_with_data(db: AsyncSession) -> TrendAnalysis | None:
    """Get the most recent TrendAnalysis that has actual topic data."""
    result = await db.execute(
        select(TrendAnalysis).order_by(TrendAnalysis.analyzed_at.desc()).limit(10)
    )
    for trend in result.scalars().all():
        if trend.topics and len(trend.topics) > 0:
            return trend
    return None


@router.get("/")
async def get_latest_trends(db: AsyncSession = Depends(get_db)):
    """Get the most recent trend analysis with actual data."""
    trend = await _get_latest_with_data(db)
    if not trend:
        return {"message": "No trend analysis yet. Run a pipeline first."}
    return {
        "id": trend.id,
        "topics": trend.topics,
        "opportunities": trend.opportunities,
        "sentiment_summary": trend.sentiment_summary,
        "analyzed_at": trend.analyzed_at.isoformat() if trend.analyzed_at else None,
    }


@router.get("/topics")
async def get_topics(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get hot topics from recent analyses."""
    trend = await _get_latest_with_data(db)
    if not trend:
        return []
    return (trend.topics or [])[:limit]


@router.get("/opportunities")
async def get_opportunities(db: AsyncSession = Depends(get_db)):
    """Get Verse8-relevant opportunities."""
    trend = await _get_latest_with_data(db)
    if not trend:
        return []
    return trend.opportunities or []
