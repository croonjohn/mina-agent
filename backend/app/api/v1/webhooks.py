"""Webhook registration API."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.models.models import Webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

VALID_EVENTS = [
    "promotion.analyzing",
    "promotion.generating",
    "promotion.ready",
    "promotion.failed",
    "content.generated",
    "content.approved",
    "content.published",
    "pipeline.completed",
]


class WebhookCreate(BaseModel):
    url: str
    events: list[str] = VALID_EVENTS
    secret: str | None = None
    owner: str | None = None


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: list[str]
    owner: str | None
    active: bool


@router.post("/", response_model=WebhookResponse)
async def register_webhook(
    request: WebhookCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a webhook URL to receive events from Mina.

    Available events:
    - `promotion.analyzing` — Mina started analyzing trends for a promotion
    - `promotion.generating` — Mina is generating content
    - `promotion.ready` — Content generated and queued for review
    - `promotion.failed` — Promotion failed
    - `content.generated` — New content created
    - `content.approved` — Content approved for publishing
    - `content.published` — Content published to platform
    - `pipeline.completed` — Pipeline run finished

    Webhook payload includes `X-Mina-Event` header and optional
    `X-Mina-Signature` (HMAC-SHA256) if secret is provided.
    """
    hook = Webhook(
        url=request.url,
        events=request.events,
        secret=request.secret,
        owner=request.owner,
    )
    db.add(hook)
    await db.commit()
    await db.refresh(hook)
    return WebhookResponse(
        id=hook.id, url=hook.url, events=hook.events,
        owner=hook.owner, active=hook.active,
    )


@router.get("/")
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    """List all registered webhooks."""
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    hooks = result.scalars().all()
    return [
        {"id": h.id, "url": h.url, "events": h.events, "owner": h.owner, "active": h.active}
        for h in hooks
    ]


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: int, db: AsyncSession = Depends(get_db)):
    """Remove a webhook."""
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    hook = result.scalar_one_or_none()
    if not hook:
        return {"error": "Webhook not found"}
    await db.delete(hook)
    await db.commit()
    return {"deleted": True}


@router.get("/events")
async def list_available_events():
    """List all available webhook events."""
    return {"events": VALID_EVENTS}
