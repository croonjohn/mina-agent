"""Escalation management API endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sql_func
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.models import Escalation

router = APIRouter(prefix="/escalations", tags=["escalations"])


# --- Pydantic schemas ---

class ResolveRequest(BaseModel):
    resolution_note: Optional[str] = None


class RespondRequest(BaseModel):
    response_text: str


# --- Endpoints ---

@router.get("/")
async def list_escalations(
    status: Optional[str] = None,
    level: Optional[int] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    List escalations with optional filters.

    - **status**: open, resolved, dismissed
    - **level**: 1-5 severity level
    """
    query = select(Escalation).order_by(Escalation.created_at.desc()).limit(limit)
    if status:
        query = query.where(Escalation.status == status)
    if level is not None:
        query = query.where(Escalation.level == level)

    result = await db.execute(query)
    items = result.scalars().all()
    return [_serialize(e) for e in items]


@router.get("/count")
async def count_open_escalations(db: AsyncSession = Depends(get_db)):
    """Return the number of open escalations."""
    result = await db.execute(
        select(sql_func.count()).select_from(Escalation).where(Escalation.status == "open")
    )
    count = result.scalar()
    return {"count": count}


@router.get("/{escalation_id}")
async def get_escalation(escalation_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single escalation by ID."""
    result = await db.execute(select(Escalation).where(Escalation.id == escalation_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return _serialize(item)


@router.post("/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: int,
    data: ResolveRequest = ResolveRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Mark an escalation as resolved."""
    result = await db.execute(select(Escalation).where(Escalation.id == escalation_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if item.status == "resolved":
        raise HTTPException(status_code=400, detail="Escalation is already resolved")

    item.status = "resolved"
    item.resolved_at = datetime.now(timezone.utc)

    # Append resolution note to description if provided
    if data.resolution_note:
        item.description = (
            f"{item.description}\n\n--- Resolution ---\n{data.resolution_note}"
        )

    await db.commit()
    await db.refresh(item)
    return _serialize(item)


@router.post("/{escalation_id}/respond")
async def respond_to_escalation(
    escalation_id: int,
    data: RespondRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a human response to an escalation.
    Stores the response as the AI draft response for publishing.
    """
    result = await db.execute(select(Escalation).where(Escalation.id == escalation_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Escalation not found")

    item.ai_draft_response = data.response_text
    await db.commit()
    await db.refresh(item)
    return _serialize(item)


@router.post("/{escalation_id}/dismiss")
async def dismiss_escalation(
    escalation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mark an escalation as dismissed."""
    result = await db.execute(select(Escalation).where(Escalation.id == escalation_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Escalation not found")

    if item.status == "dismissed":
        raise HTTPException(status_code=400, detail="Escalation is already dismissed")

    item.status = "dismissed"
    item.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(item)
    return _serialize(item)


# --- Helpers ---

def _serialize(e: Escalation) -> dict:
    return {
        "id": e.id,
        "published_post_id": e.published_post_id,
        "level": e.level,
        "trigger_type": e.trigger_type,
        "description": e.description,
        "ai_draft_response": e.ai_draft_response,
        "status": e.status,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
    }
