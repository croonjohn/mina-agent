"""Devvit bridge API — endpoints for Devvit app to poll and acknowledge tasks."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import ContentItem, PublishedPost

router = APIRouter(prefix="/devvit", tags=["devvit-bridge"])


def verify_api_key(x_api_key: str = Header(...)):
    """Simple API key auth for Devvit app."""
    settings = get_settings()
    if x_api_key != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


class AckRequest(BaseModel):
    content_id: int
    external_id: str
    external_url: str


class AckResponse(BaseModel):
    success: bool
    published_post_id: Optional[int] = None


@router.get("/tasks", dependencies=[Depends(verify_api_key)])
async def get_pending_tasks(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns approved Reddit content items ready for Devvit to publish.
    The Devvit scheduler polls this endpoint periodically.
    """
    result = await db.execute(
        select(ContentItem)
        .where(ContentItem.platform == "reddit")
        .where(ContentItem.status == "approved")
        .order_by(ContentItem.approved_at.asc())
        .limit(limit)
    )
    items = result.scalars().all()

    return [
        {
            "id": item.id,
            "target": item.target,
            "content_type": item.content_type,
            "title": item.title,
            "body": item.body,
            "template_id": item.template_id,
        }
        for item in items
    ]


@router.post("/ack", response_model=AckResponse, dependencies=[Depends(verify_api_key)])
async def acknowledge_publish(
    request: AckRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Devvit calls this after successfully posting to Reddit.
    Updates content status and creates PublishedPost record.
    """
    result = await db.execute(
        select(ContentItem).where(ContentItem.id == request.content_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    if item.status == "published":
        return AckResponse(success=True, published_post_id=None)

    # Create published post record
    published = PublishedPost(
        content_id=item.id,
        platform="reddit",
        external_url=request.external_url,
        external_id=request.external_id,
    )
    db.add(published)

    # Update content status
    item.status = "published"
    item.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(published)

    return AckResponse(success=True, published_post_id=published.id)


@router.post("/error", dependencies=[Depends(verify_api_key)])
async def report_error(
    content_id: int,
    error: str,
    db: AsyncSession = Depends(get_db),
):
    """Devvit reports a publish failure."""
    result = await db.execute(
        select(ContentItem).where(ContentItem.id == content_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    item.status = "failed"
    await db.commit()
    return {"success": True, "content_id": content_id, "status": "failed"}


@router.get("/health")
async def devvit_health():
    """Health check for Devvit app connectivity test."""
    return {"status": "ok", "service": "mina-agent-devvit-bridge"}
