"""System administration API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.cleanup import cleanup_old_data

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/cleanup")
async def run_cleanup(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete old ScrapedPost records for data retention.

    - **days**: Delete records older than this many days (default 30)
    """
    result = await cleanup_old_data(db=db, days=days)
    return result
