"""Content queue API endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.models import ContentItem
from app.services.content_rules import validate_content

router = APIRouter(prefix="/content", tags=["content"])


class ContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None


class ContentGenerateRequest(BaseModel):
    content_type: str = "post"
    platform: str = "reddit"
    target: str = "gamedev"
    context: dict = {}
    template_id: Optional[str] = None


class BatchActionRequest(BaseModel):
    content_ids: list[int]


@router.get("/queue")
async def get_content_queue(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get content queue with optional filters."""
    query = select(ContentItem).order_by(ContentItem.created_at.desc()).limit(limit)
    if status:
        query = query.where(ContentItem.status == status)
    if platform:
        query = query.where(ContentItem.platform == platform)

    result = await db.execute(query)
    items = result.scalars().all()
    return [_serialize_content(item) for item in items]


@router.get("/{content_id}")
async def get_content(content_id: int, db: AsyncSession = Depends(get_db)):
    """Get content item by ID."""
    result = await db.execute(select(ContentItem).where(ContentItem.id == content_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    return _serialize_content(item)


@router.put("/{content_id}")
async def update_content(content_id: int, update_data: ContentUpdate, db: AsyncSession = Depends(get_db)):
    """Update content item (edit before publishing)."""
    result = await db.execute(select(ContentItem).where(ContentItem.id == content_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    if update_data.title is not None:
        item.title = update_data.title
    if update_data.body is not None:
        item.body = update_data.body
    await db.commit()
    return _serialize_content(item)


@router.delete("/{content_id}")
async def delete_content(content_id: int, db: AsyncSession = Depends(get_db)):
    """Delete content item."""
    result = await db.execute(select(ContentItem).where(ContentItem.id == content_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    await db.delete(item)
    await db.commit()
    return {"deleted": True}


@router.post("/{content_id}/approve")
async def approve_content(content_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a content item for publishing."""
    result = await db.execute(select(ContentItem).where(ContentItem.id == content_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    item.status = "approved"
    item.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return _serialize_content(item)


@router.post("/{content_id}/reject")
async def reject_content(content_id: int, db: AsyncSession = Depends(get_db)):
    """Reject a content item."""
    result = await db.execute(select(ContentItem).where(ContentItem.id == content_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    item.status = "rejected"
    await db.commit()
    return _serialize_content(item)


@router.post("/batch-approve")
async def batch_approve(request: BatchActionRequest, db: AsyncSession = Depends(get_db)):
    """Approve multiple content items."""
    await db.execute(
        update(ContentItem)
        .where(ContentItem.id.in_(request.content_ids))
        .values(status="approved", approved_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"approved": len(request.content_ids)}


@router.post("/batch-reject")
async def batch_reject(request: BatchActionRequest, db: AsyncSession = Depends(get_db)):
    """Reject multiple content items."""
    await db.execute(
        update(ContentItem)
        .where(ContentItem.id.in_(request.content_ids))
        .values(status="rejected")
    )
    await db.commit()
    return {"rejected": len(request.content_ids)}


@router.post("/generate")
async def generate_content(request: ContentGenerateRequest, db: AsyncSession = Depends(get_db)):
    """Manually generate content using Claude Code CLI."""
    from app.services.trend_analyzer import generate_content_with_claude

    result = await generate_content_with_claude(
        content_type=request.content_type,
        platform=request.platform,
        target=request.target,
        trend_context=request.context,
    )

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    item = ContentItem(
        platform=result.get("platform", request.platform),
        target=result.get("target", request.target),
        content_type=result.get("content_type", request.content_type),
        title=result.get("title"),
        body=result.get("body", ""),
        trend_context=request.context,
        status="pending",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _serialize_content(item)


class ValidateRequest(BaseModel):
    text: str


@router.post("/validate")
async def validate_content_text(request: ValidateRequest):
    """Validate content against Content Rules (AI-tell detection, promo density, etc.)."""
    result = validate_content(request.text)
    return result


@router.post("/{content_id}/validate")
async def validate_content_item(content_id: int, db: AsyncSession = Depends(get_db)):
    """Validate a specific content item against Content Rules."""
    result = await db.execute(select(ContentItem).where(ContentItem.id == content_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")

    body_result = validate_content(item.body or "")
    title_result = validate_content(item.title or "") if item.title else {"valid": True, "issues": [], "cleaned": item.title or ""}

    return {
        "content_id": content_id,
        "body_validation": body_result,
        "title_validation": title_result,
    }


def _serialize_content(item: ContentItem) -> dict:
    # Run quick validation for display
    body_check = validate_content(item.body or "") if item.body else None

    return {
        "id": item.id,
        "pipeline_id": str(item.pipeline_id) if item.pipeline_id else None,
        "platform": item.platform,
        "target": item.target,
        "content_type": item.content_type,
        "title": item.title,
        "body": item.body,
        "image_url": item.image_url,
        "template_id": item.template_id,
        "trend_context": item.trend_context,
        "source_post_url": item.source_post_url,
        "status": item.status,
        "content_rules": {
            "valid": body_check["valid"] if body_check else True,
            "issues": body_check["issues"] if body_check else [],
        } if body_check else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        "published_at": item.published_at.isoformat() if item.published_at else None,
    }
