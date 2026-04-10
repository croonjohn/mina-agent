"""Templates CRUD API endpoints."""
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.models import Template


def _slugify(name: str) -> str:
    """Generate a URL-safe slug from a template name.
    e.g. "Reddit Post Template" -> "reddit-post-template"
    """
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")

router = APIRouter(prefix="/templates", tags=["templates"])


# --- Pydantic schemas ---

class TemplateCreate(BaseModel):
    id: Optional[str] = None
    name: str
    platform: str
    content_type: str
    template_text: str
    variables: list[str] = []


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    content_type: Optional[str] = None
    template_text: Optional[str] = None
    variables: Optional[list[str]] = None


# --- Default seed templates ---

DEFAULT_TEMPLATES = [
    {
        "id": "reddit-post",
        "name": "Reddit Post",
        "platform": "reddit",
        "content_type": "post",
        "template_text": (
            "Title: {title}\n\n"
            "{body}\n\n"
            "---\n"
            "What do you think? I'd love to hear your feedback!"
        ),
        "variables": ["title", "body"],
    },
    {
        "id": "reddit-comment",
        "name": "Reddit Comment",
        "platform": "reddit",
        "content_type": "comment",
        "template_text": (
            "{body}\n\n"
            "If you're interested, you can check it out here: {link}"
        ),
        "variables": ["body", "link"],
    },
    {
        "id": "itchio-devlog",
        "name": "itch.io Devlog",
        "platform": "itchio",
        "content_type": "devlog",
        "template_text": (
            "# {title}\n\n"
            "{body}\n\n"
            "## What's Next\n"
            "{next_steps}\n\n"
            "Thanks for following along! Your support means a lot."
        ),
        "variables": ["title", "body", "next_steps"],
    },
    {
        "id": "itchio-community-post",
        "name": "itch.io Community Post",
        "platform": "itchio",
        "content_type": "community_post",
        "template_text": (
            "**{title}**\n\n"
            "{body}\n\n"
            "Let me know what you think in the comments!"
        ),
        "variables": ["title", "body"],
    },
    {
        "id": "itchio-reply",
        "name": "itch.io Reply",
        "platform": "itchio",
        "content_type": "reply",
        "template_text": (
            "Hey, thanks for your comment!\n\n"
            "{body}\n\n"
            "Really appreciate the feedback."
        ),
        "variables": ["body"],
    },
]


# --- Endpoints ---

@router.get("/")
async def list_templates(
    platform: Optional[str] = None,
    content_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all templates with optional platform/content_type filters."""
    query = select(Template).order_by(Template.id)
    if platform:
        query = query.where(Template.platform == platform)
    if content_type:
        query = query.where(Template.content_type == content_type)

    result = await db.execute(query)
    items = result.scalars().all()
    return [_serialize(t) for t in items]


@router.get("/{template_id}")
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single template by ID."""
    result = await db.execute(select(Template).where(Template.id == template_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Template not found")
    return _serialize(item)


@router.post("/")
async def create_template(data: TemplateCreate, db: AsyncSession = Depends(get_db)):
    """Create a new template."""
    # Auto-generate ID from name if not provided
    template_id = data.id if data.id else _slugify(data.name)

    # Check for duplicate ID
    existing = await db.execute(select(Template).where(Template.id == template_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Template with id '{template_id}' already exists")

    item = Template(
        id=template_id,
        name=data.name,
        platform=data.platform,
        content_type=data.content_type,
        template_text=data.template_text,
        variables=data.variables,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _serialize(item)


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    data: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing template."""
    result = await db.execute(select(Template).where(Template.id == template_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Template not found")

    if data.name is not None:
        item.name = data.name
    if data.platform is not None:
        item.platform = data.platform
    if data.content_type is not None:
        item.content_type = data.content_type
    if data.template_text is not None:
        item.template_text = data.template_text
    if data.variables is not None:
        item.variables = data.variables

    await db.commit()
    await db.refresh(item)
    return _serialize(item)


@router.delete("/{template_id}")
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a template."""
    result = await db.execute(select(Template).where(Template.id == template_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(item)
    await db.commit()
    return {"deleted": True}


@router.post("/seed")
async def seed_templates(db: AsyncSession = Depends(get_db)):
    """Insert default templates. Skips any that already exist."""
    created = 0
    skipped = 0
    for tpl_data in DEFAULT_TEMPLATES:
        existing = await db.execute(select(Template).where(Template.id == tpl_data["id"]))
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        item = Template(**tpl_data)
        db.add(item)
        created += 1

    await db.commit()
    return {"created": created, "skipped": skipped, "total_defaults": len(DEFAULT_TEMPLATES)}


# --- Helpers ---

def _serialize(t: Template) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "platform": t.platform,
        "content_type": t.content_type,
        "template_text": t.template_text,
        "variables": t.variables,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }
