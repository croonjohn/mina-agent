"""Tone guidelines API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.models import ToneGuideline

router = APIRouter(prefix="/guidelines", tags=["guidelines"])


# --- Default Mina Lee persona guidelines ---

DEFAULT_GUIDELINES = {
    "use_words": [
        "pretty cool",
        "honestly",
        "fun",
        "neat",
        "really like",
        "check it out",
        "been working on",
        "thought you might enjoy",
        "super helpful",
        "give it a try",
    ],
    "avoid_words": [
        "revolutionize",
        "game-changer",
        "unleash",
        "synergy",
        "disrupt",
        "leverage",
        "paradigm shift",
        "cutting-edge",
        "best-in-class",
        "next-gen",
    ],
    "principles": [
        "Be casual but professional — like a fellow indie dev chatting in a community",
        "Avoid corporate jargon and marketing-speak",
        "Show genuine enthusiasm without being over-the-top",
        "Ask questions to engage the community, don't just broadcast",
        "Share useful info or personal experience — add value to the conversation",
        "Use first person naturally (I, we) — don't sound like a press release",
        "Keep it concise — respect people's time",
        "Match the tone of the community you're posting in",
    ],
}


# --- Pydantic schemas ---

class ToneGuidelineUpdate(BaseModel):
    use_words: Optional[list[str]] = None
    avoid_words: Optional[list[str]] = None
    principles: Optional[list[str]] = None


# --- Endpoints ---

@router.get("/tone")
async def get_tone_guidelines(db: AsyncSession = Depends(get_db)):
    """
    Return current tone guidelines.
    Auto-creates default Mina Lee persona guidelines if none exist.
    """
    result = await db.execute(select(ToneGuideline).order_by(ToneGuideline.id.desc()).limit(1))
    guideline = result.scalar_one_or_none()

    if not guideline:
        # Auto-create default guidelines
        guideline = ToneGuideline(
            use_words=DEFAULT_GUIDELINES["use_words"],
            avoid_words=DEFAULT_GUIDELINES["avoid_words"],
            principles=DEFAULT_GUIDELINES["principles"],
        )
        db.add(guideline)
        await db.commit()
        await db.refresh(guideline)

    return _serialize(guideline)


@router.put("/tone")
async def update_tone_guidelines(
    data: ToneGuidelineUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update tone guidelines. Creates if none exist."""
    result = await db.execute(select(ToneGuideline).order_by(ToneGuideline.id.desc()).limit(1))
    guideline = result.scalar_one_or_none()

    if not guideline:
        # Create new with defaults, then apply updates
        guideline = ToneGuideline(
            use_words=DEFAULT_GUIDELINES["use_words"],
            avoid_words=DEFAULT_GUIDELINES["avoid_words"],
            principles=DEFAULT_GUIDELINES["principles"],
        )
        db.add(guideline)
        await db.flush()

    if data.use_words is not None:
        guideline.use_words = data.use_words
    if data.avoid_words is not None:
        guideline.avoid_words = data.avoid_words
    if data.principles is not None:
        guideline.principles = data.principles

    await db.commit()
    await db.refresh(guideline)
    return _serialize(guideline)


# --- Helpers ---

def _serialize(g: ToneGuideline) -> dict:
    return {
        "id": g.id,
        "use_words": g.use_words,
        "avoid_words": g.avoid_words,
        "principles": g.principles,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
    }
