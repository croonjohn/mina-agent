"""Publish API endpoints — semi-automatic (copy + link) workflow.

Both Reddit and itch.io use the same flow:
1. Pipeline generates content
2. Admin reviews/edits in dashboard
3. Admin clicks "Copy" → clipboard + opens target URL
4. Admin pastes content manually on the platform

No automated posting (Reddit API blocked for new apps, Playwright risky for bot detection).
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.models import ContentItem, PublishedPost
from app.services.publisher import prepare_reddit_publish, prepare_itchio_content

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/publish", tags=["publish"])


class PublishRequest(BaseModel):
    content_id: int


class MarkPublishedRequest(BaseModel):
    content_id: int
    external_url: Optional[str] = None


# ─── Board/Subreddit URL helpers ────────────────────────────────────────────

REDDIT_POST_URL = "https://www.reddit.com/r/{target}/submit?type=self"
REDDIT_COMMENT_BASE = "https://www.reddit.com/r/{target}"

ITCHIO_BOARD_URLS = {
    "release-announcements": "https://itch.io/board/10022/release-announcements",
    "game-development": "https://itch.io/board/10020/game-development",
    "everything-else": "https://itch.io/board/10027/everything-else",
    "devlogs": "https://itch.io/dashboard/games",
}


def _get_target_url(platform: str, target: str, content_type: str, source_post_url: str = "") -> str:
    """Return the URL where the user should manually paste the content."""
    if platform == "reddit":
        if content_type == "comment" and source_post_url:
            return source_post_url
        return REDDIT_POST_URL.format(target=target)
    elif platform == "itchio":
        return ITCHIO_BOARD_URLS.get(target, f"https://itch.io/community")
    return ""


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/")
async def publish_content(request: PublishRequest, db: AsyncSession = Depends(get_db)):
    """
    Prepare content for manual publishing (copy + paste).
    Returns the content to copy and the target URL to open.
    """
    result = await db.execute(select(ContentItem).where(ContentItem.id == request.content_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    if item.status not in ("approved", "pending"):
        raise HTTPException(status_code=400, detail=f"Content status is '{item.status}', must be 'approved' or 'pending'")

    # Mark as ready to publish
    item.status = "approved"
    item.approved_at = datetime.now(timezone.utc)
    await db.commit()

    target_url = _get_target_url(
        platform=item.platform,
        target=item.target,
        content_type=item.content_type,
        source_post_url=item.source_post_url or "",
    )

    return {
        "success": True,
        "content_id": item.id,
        "platform": item.platform,
        "method": "manual_copy",
        "target_url": target_url,
        "title": item.title,
        "body": item.body,
        "content_type": item.content_type,
        "instructions": f"1. Copy the content\n2. Open {target_url}\n3. Paste and submit",
    }


@router.post("/mark-published")
async def mark_as_published(request: MarkPublishedRequest, db: AsyncSession = Depends(get_db)):
    """
    Mark content as published after the user manually posts it.
    Optionally provide the external URL of the published post.
    """
    result = await db.execute(select(ContentItem).where(ContentItem.id == request.content_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    item.status = "published"
    item.published_at = datetime.now(timezone.utc)

    pub = PublishedPost(
        content_id=request.content_id,
        platform=item.platform,
        external_url=request.external_url or "",
        external_id=request.external_url or "",
    )
    db.add(pub)
    await db.commit()

    return {"success": True, "content_id": item.id, "status": "published"}


@router.post("/batch")
async def publish_batch(db: AsyncSession = Depends(get_db)):
    """Prepare all approved/pending items for manual publishing."""
    result = await db.execute(
        select(ContentItem)
        .where(ContentItem.status.in_(["approved", "pending"]))
        .order_by(ContentItem.created_at)
    )
    items = result.scalars().all()

    results = []
    now = datetime.now(timezone.utc)

    for item in items:
        item.status = "approved"
        item.approved_at = now

        target_url = _get_target_url(
            platform=item.platform,
            target=item.target,
            content_type=item.content_type,
            source_post_url=item.source_post_url or "",
        )

        results.append({
            "content_id": item.id,
            "success": True,
            "platform": item.platform,
            "method": "manual_copy",
            "target_url": target_url,
        })

    await db.commit()
    return {"queued": len(results), "results": results}


@router.get("/history")
async def get_publish_history(
    platform: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get published posts history."""
    query = select(PublishedPost).order_by(PublishedPost.published_at.desc()).limit(limit)
    if platform:
        query = query.where(PublishedPost.platform == platform)
    result = await db.execute(query)
    posts = result.scalars().all()
    return [
        {
            "id": p.id,
            "content_id": p.content_id,
            "platform": p.platform,
            "external_url": p.external_url,
            "score": p.score,
            "comment_count": p.comment_count,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in posts
    ]
