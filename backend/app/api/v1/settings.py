"""Settings API endpoints for dashboard configuration."""
import json
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.config import get_settings
from app.scrapers.reddit_scraper import SUBREDDIT_TIERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

# Persistent storage paths
_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_SUBREDDIT_CONFIG = _DATA_DIR / "subreddit_config.json"
_SETTINGS_FILE = _DATA_DIR / "settings.json"


# --- Helpers ---

def _ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: dict | list) -> dict | list:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def _write_json(path: Path, data: dict | list) -> None:
    _ensure_data_dir()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# --- Pydantic schemas ---

class SubredditAdd(BaseModel):
    name: str
    tier: int


class DiscordWebhookUpdate(BaseModel):
    url: str


# --- Subreddit endpoints ---

@router.get("/subreddits")
async def get_subreddits():
    """Return current subreddit tiers.

    Merges the hardcoded defaults from reddit_scraper.py with any
    user-added subreddits stored in data/subreddit_config.json.
    """
    # Start with defaults
    tiers: dict[int, list[str]] = {int(k): list(v) for k, v in SUBREDDIT_TIERS.items()}

    # Overlay user config
    user_config = _read_json(_SUBREDDIT_CONFIG, {})
    if isinstance(user_config, dict):
        for tier_str, subs in user_config.items():
            tier = int(tier_str)
            if tier not in tiers:
                tiers[tier] = []
            for sub in subs:
                if sub not in tiers[tier]:
                    tiers[tier].append(sub)

    return {"subreddit_tiers": tiers}


@router.post("/subreddits")
async def add_subreddit(data: SubredditAdd):
    """Add a subreddit to a tier. Persists to data/subreddit_config.json."""
    if not 1 <= data.tier <= 10:
        raise HTTPException(status_code=400, detail="Tier must be between 1 and 10")

    name = data.name.strip().lstrip("r/")
    if not name:
        raise HTTPException(status_code=400, detail="Subreddit name is required")

    user_config: dict = _read_json(_SUBREDDIT_CONFIG, {})
    tier_key = str(data.tier)

    if tier_key not in user_config:
        user_config[tier_key] = []

    if name in user_config[tier_key]:
        raise HTTPException(status_code=409, detail=f"r/{name} already exists in tier {data.tier}")

    user_config[tier_key].append(name)
    _write_json(_SUBREDDIT_CONFIG, user_config)

    return {"added": name, "tier": data.tier}


@router.delete("/subreddits/{name}")
async def remove_subreddit(name: str):
    """Remove a subreddit from user config."""
    user_config: dict = _read_json(_SUBREDDIT_CONFIG, {})
    removed = False

    for tier_key in list(user_config.keys()):
        subs = user_config[tier_key]
        if name in subs:
            subs.remove(name)
            removed = True
            if not subs:
                del user_config[tier_key]

    if not removed:
        raise HTTPException(status_code=404, detail=f"r/{name} not found in user config")

    _write_json(_SUBREDDIT_CONFIG, user_config)
    return {"removed": name}


# --- Discord webhook endpoints ---

def _get_stored_settings() -> dict:
    return _read_json(_SETTINGS_FILE, {})


def _save_stored_settings(data: dict) -> None:
    _write_json(_SETTINGS_FILE, data)


@router.get("/discord-webhook")
async def get_discord_webhook():
    """Return current Discord webhook URL."""
    stored = _get_stored_settings()
    url = stored.get("discord_webhook_url") or get_settings().discord_webhook_url
    return {"url": url}


@router.put("/discord-webhook")
async def update_discord_webhook(data: DiscordWebhookUpdate):
    """Update Discord webhook URL (persisted in data/settings.json)."""
    stored = _get_stored_settings()
    stored["discord_webhook_url"] = data.url
    _save_stored_settings(stored)
    return {"url": data.url, "updated": True}


@router.post("/discord-webhook/test")
async def test_discord_webhook():
    """Send a test message to the configured Discord webhook URL."""
    stored = _get_stored_settings()
    url = stored.get("discord_webhook_url") or get_settings().discord_webhook_url

    if not url:
        raise HTTPException(status_code=400, detail="No Discord webhook URL configured")

    payload = {
        "content": "Mina Agent test message -- webhook is working!",
        "username": "Mina Agent",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Discord returned HTTP {e.response.status_code}",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to send test message: {e}")

    return {"success": True, "message": "Test message sent"}
