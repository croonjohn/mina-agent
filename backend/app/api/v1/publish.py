"""Publish API endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.models import ContentItem, PublishedPost
from app.services.publisher import prepare_reddit_publish, prepare_itchio_content

router = APIRouter(prefix="/publish", tags=["publish"])


class PublishRequest(BaseModel):
    content_id: int


class ItchioPostRequest(BaseModel):
    board: str
    title: str
    content: str


@router.post("/")
async def publish_content(request: PublishRequest, db: AsyncSession = Depends(get_db)):
    """
    Publish a single content item.
    - Reddit: approves for Devvit pickup (auto-posted by Devvit scheduler)
    - itch.io: returns copy-paste instructions
    """
    result = await db.execute(select(ContentItem).where(ContentItem.id == request.content_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    if item.status not in ("approved", "pending"):
        raise HTTPException(status_code=400, detail=f"Content status is '{item.status}', must be 'approved' or 'pending'")

    if item.platform == "reddit":
        # Mark as approved — Devvit scheduler will pick it up
        item.status = "approved"
        item.approved_at = datetime.now(timezone.utc)
        await db.commit()

        pub_info = prepare_reddit_publish(
            target=item.target,
            title=item.title or "",
            body=item.body,
            content_type=item.content_type,
        )
        return {"success": True, "content_id": item.id, **pub_info}

    elif item.platform == "itchio":
        itchio_data = prepare_itchio_content(
            title=item.title or "",
            body=item.body,
            board=item.target,
        )
        return {"success": True, "manual_post": True, **itchio_data}

    raise HTTPException(status_code=400, detail=f"Unsupported platform: {item.platform}")


@router.post("/batch")
async def publish_batch(db: AsyncSession = Depends(get_db)):
    """Approve all approved/pending content items for publishing."""
    result = await db.execute(
        select(ContentItem)
        .where(ContentItem.status.in_(["approved", "pending"]))
        .order_by(ContentItem.created_at)
    )
    items = result.scalars().all()

    results = []
    now = datetime.now(timezone.utc)

    for item in items:
        if item.platform == "reddit":
            item.status = "approved"
            item.approved_at = now
            results.append({
                "content_id": item.id,
                "success": True,
                "method": "devvit",
                "status": "queued_for_devvit",
            })
        elif item.platform == "itchio":
            itchio_data = prepare_itchio_content(item.title or "", item.body, item.target)
            results.append({"content_id": item.id, "success": True, "manual_post": True, **itchio_data})

    await db.commit()
    return {"queued": len([r for r in results if r.get("success")]), "results": results}


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


@router.post("/itchio/post")
async def prepare_itchio_post(request: ItchioPostRequest):
    """Prepare itch.io post for manual copy-paste."""
    return prepare_itchio_content(request.title, request.content, request.board)
