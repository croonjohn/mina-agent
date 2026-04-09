"""Webhook delivery service."""
import hashlib
import hmac
import json
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Webhook

logger = logging.getLogger(__name__)


async def fire_event(db: AsyncSession, event: str, payload: dict):
    """Send webhook to all subscribers of this event."""
    result = await db.execute(
        select(Webhook).where(Webhook.active == True)
    )
    hooks = result.scalars().all()

    for hook in hooks:
        if event not in (hook.events or []):
            continue
        try:
            await _deliver(hook.url, event, payload, hook.secret)
        except Exception as e:
            logger.warning("[Webhook] Failed to deliver %s to %s: %s", event, hook.url, e)


async def fire_callback(url: str, event: str, payload: dict, secret: str = None):
    """Send a direct callback to a specific URL (for promotion callbacks)."""
    try:
        await _deliver(url, event, payload, secret)
    except Exception as e:
        logger.warning("[Webhook] Callback failed %s to %s: %s", event, url, e)


async def _deliver(url: str, event: str, payload: dict, secret: str = None):
    body = json.dumps({"event": event, **payload}, ensure_ascii=False, default=str)
    headers = {"Content-Type": "application/json", "X-Mina-Event": event}
    if secret:
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-Mina-Signature"] = sig

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, content=body, headers=headers, timeout=10)
        logger.info("[Webhook] %s -> %s (%d)", event, url, resp.status_code)
