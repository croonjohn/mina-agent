"""Reddit scraper - HTTP JSON mode (no API keys needed, read-only)."""
import asyncio
import httpx
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Subreddit tiers from Mina Lee's plan
SUBREDDIT_TIERS = {
    1: ["gamedev", "indiegaming", "IndieDev", "itchio", "WebGames"],
    2: ["gamejams", "playmygame", "DestroyMyGame", "gamedesign", "gameideas"],
    3: ["artificial", "singularity", "ChatGPT"],
    4: ["webdev", "javascript", "html5"],
    5: ["gaming", "Games", "SideProject"],
}

HEADERS = {
    "User-Agent": "mina-agent:v1.0 (Verse8 community manager)",
}


# === HTTP JSON mode (no API key needed, read-only) ===

async def scrape_subreddit_http(
    subreddit_name: str,
    sort: str = "hot",
    limit: int = 25,
) -> list[dict]:
    """Scrape posts via Reddit's public .json endpoint. No API key needed."""
    url = f"https://www.reddit.com/r/{subreddit_name}/{sort}.json?limit={limit}&raw_json=1"
    posts = []

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

    for child in data.get("data", {}).get("children", []):
        p = child.get("data", {})
        if p.get("stickied"):
            continue

        posts.append({
            "platform": "reddit",
            "source": subreddit_name,
            "external_id": p.get("id", ""),
            "title": p.get("title", ""),
            "body": (p.get("selftext") or "")[:2000],
            "author": p.get("author", "[deleted]"),
            "url": f"https://reddit.com{p.get('permalink', '')}",
            "score": p.get("score", 0),
            "comment_count": p.get("num_comments", 0),
            "metadata": {
                "flair": p.get("link_flair_text"),
                "created_utc": p.get("created_utc"),
                "is_self": p.get("is_self"),
                "subreddit": subreddit_name,
                "upvote_ratio": p.get("upvote_ratio"),
            },
        })

    return posts


# === Main entry point ===

async def scrape_tiers(tiers: list[int], limit_per_sub: int = 25) -> list[dict]:
    """Scrape subreddits via HTTP JSON (read-only, no API key needed)."""
    logger.info("[Scraper] Using HTTP JSON mode")

    all_posts = []
    for tier in tiers:
        subreddits = SUBREDDIT_TIERS.get(tier, [])
        for sub_name in subreddits:
            try:
                posts = await scrape_subreddit_http(sub_name, limit=limit_per_sub)
                all_posts.extend(posts)
                logger.info("[Scraper] r/%s: %d posts", sub_name, len(posts))
                await asyncio.sleep(2)  # rate limit
            except Exception as e:
                logger.error("[Scraper] Error scraping r/%s: %s", sub_name, e)
                continue

    return all_posts
