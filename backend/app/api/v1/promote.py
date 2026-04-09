"""Promotion API - game studios submit promotion requests, Mina handles everything."""
from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.models.models import Promotion

router = APIRouter(prefix="/promote", tags=["promote"])


class PromotionRequest(BaseModel):
    game_title: str
    game_url: str | None = None
    game_description: str | None = None
    target_platforms: list[str] = ["reddit"]
    target_communities: list[str] = []
    extra_context: dict = {}
    callback_url: str | None = None
    requested_by: str | None = None


class PromotionResponse(BaseModel):
    promotion_id: str
    status: str
    message: str


async def _run_promotion_bg(promotion_id: UUID, db_session_factory):
    """Background task that runs the full promotion flow."""
    from app.services.promotion import run_promotion
    async with db_session_factory() as db:
        result = await db.execute(
            select(Promotion).where(Promotion.id == promotion_id)
        )
        promotion = result.scalar_one_or_none()
        if promotion:
            await run_promotion(db, promotion)


@router.post("/", response_model=PromotionResponse)
async def create_promotion(
    request: PromotionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a game for promotion. Mina will:
    1. Analyze current trends in target communities
    2. Generate tailored promotional content
    3. Queue content for review (or auto-approve)
    4. Notify via callback_url at each step

    Example:
    ```json
    {
      "game_title": "Space Puzzle Arena",
      "game_url": "https://verse8.io/games/space-puzzle",
      "game_description": "A multiplayer puzzle game with gravity mechanics",
      "target_communities": ["gamedev", "indiegaming", "WebGames"],
      "callback_url": "https://your-service.internal/webhook/mina"
    }
    ```
    """
    promotion = Promotion(
        game_title=request.game_title,
        game_url=request.game_url,
        game_description=request.game_description,
        target_platforms=request.target_platforms,
        target_communities=request.target_communities,
        extra_context=request.extra_context,
        callback_url=request.callback_url,
        requested_by=request.requested_by,
        status="pending",
    )
    db.add(promotion)
    await db.commit()
    await db.refresh(promotion)

    # Run promotion in background
    from app.core.database import async_session
    background_tasks.add_task(_run_promotion_bg, promotion.id, async_session)

    return PromotionResponse(
        promotion_id=str(promotion.id),
        status="accepted",
        message=f"Promotion for '{request.game_title}' accepted. Mina is working on it.",
    )


@router.get("/{promotion_id}")
async def get_promotion_status(
    promotion_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check promotion progress."""
    result = await db.execute(
        select(Promotion).where(Promotion.id == UUID(promotion_id))
    )
    promo = result.scalar_one_or_none()
    if not promo:
        return {"error": "Promotion not found"}

    return {
        "promotion_id": str(promo.id),
        "game_title": promo.game_title,
        "status": promo.status,
        "content_ids": promo.content_ids or [],
        "result_summary": promo.result_summary,
        "error": promo.error,
        "requested_by": promo.requested_by,
        "created_at": promo.created_at.isoformat() if promo.created_at else None,
        "completed_at": promo.completed_at.isoformat() if promo.completed_at else None,
    }


@router.get("/")
async def list_promotions(
    limit: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all promotion requests."""
    query = select(Promotion).order_by(Promotion.created_at.desc()).limit(limit)
    if status:
        query = query.where(Promotion.status == status)
    result = await db.execute(query)
    promos = result.scalars().all()
    return [
        {
            "promotion_id": str(p.id),
            "game_title": p.game_title,
            "status": p.status,
            "content_count": len(p.content_ids or []),
            "requested_by": p.requested_by,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in promos
    ]
