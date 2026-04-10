"""Data retention cleanup service."""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.models.models import ScrapedPost

logger = logging.getLogger(__name__)


async def cleanup_old_data(db: AsyncSession, days: int = 30) -> dict:
    """
    Delete ScrapedPost records older than `days` days.
    Returns a summary of what was cleaned up.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    logger.info("[Cleanup] Deleting ScrapedPost records older than %d days (before %s)", days, cutoff.isoformat())

    result = await db.execute(
        delete(ScrapedPost).where(ScrapedPost.scraped_at < cutoff)
    )
    deleted_count = result.rowcount
    await db.commit()

    logger.info("[Cleanup] Deleted %d old ScrapedPost records", deleted_count)

    return {
        "deleted_scraped_posts": deleted_count,
        "cutoff_date": cutoff.isoformat(),
        "days": days,
    }
