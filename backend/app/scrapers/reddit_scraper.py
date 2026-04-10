"""Reddit scraper - HTTP JSON mode (no API keys needed, read-only).

Features:
- Retry with exponential backoff (3 retries: 5s, 10s, 20s)
- User-Agent rotation from a pool of realistic browser UAs
- old.reddit.com fallback when reddit.com returns 403
- Graceful skip on all retries failing (don't crash pipeline)
"""
import asyncio
import random
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

# Pool of realistic browser User-Agent strings for rotation
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
]

# Retry config: 3 retries with exponential backoff (5s, 10s, 20s)
RETRY_DELAYS = [5, 10, 20]


def _get_headers() -> dict:
    """Return request headers with a randomly selected User-Agent."""
    return {
        "User-Agent": random.choice(USER_AGENT_POOL),
        "Accept": "application/json, text/html;q=0.9",
        "Accept-Language": "en-US,en;q=0.5",
    }


async def _fetch_subreddit_json(
    subreddit_name: str,
    sort: str = "hot",
    limit: int = 25,
) -> dict:
    """
    Fetch subreddit JSON with retry + exponential backoff + old.reddit.com fallback.

    Tries reddit.com first. On 403, falls back to old.reddit.com.
    Retries up to 3 times with delays of 5s, 10s, 20s.
    Raises on all retries failing.
    """
    urls = [
        f"https://www.reddit.com/r/{subreddit_name}/{sort}.json?limit={limit}&raw_json=1",
        f"https://old.reddit.com/r/{subreddit_name}/{sort}.json?limit={limit}&raw_json=1",
    ]

    last_error = None

    for attempt, delay in enumerate(RETRY_DELAYS):
        # On first attempt use reddit.com, on subsequent retries try old.reddit.com as well
        urls_to_try = urls if attempt > 0 else urls[:1]

        for url in urls_to_try:
            try:
                headers = _get_headers()
                async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
                    resp = await client.get(url, timeout=15)

                    if resp.status_code == 403:
                        logger.warning(
                            "[Scraper] 403 from %s (attempt %d/%d)",
                            url, attempt + 1, len(RETRY_DELAYS),
                        )
                        last_error = Exception(f"403 Forbidden: {url}")
                        continue  # Try next URL or retry

                    resp.raise_for_status()
                    return resp.json()

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "[Scraper] HTTP %d from %s (attempt %d/%d): %s",
                    e.response.status_code, url, attempt + 1, len(RETRY_DELAYS), e,
                )
                last_error = e
            except Exception as e:
                logger.warning(
                    "[Scraper] Error fetching %s (attempt %d/%d): %s",
                    url, attempt + 1, len(RETRY_DELAYS), e,
                )
                last_error = e

        # Wait before next retry (exponential backoff)
        if attempt < len(RETRY_DELAYS) - 1:
            logger.info("[Scraper] Waiting %ds before retry %d...", delay, attempt + 2)
            await asyncio.sleep(delay)

    # All retries exhausted
    raise last_error or Exception(f"Failed to fetch r/{subreddit_name} after all retries")


# === HTTP JSON mode (no API key needed, read-only) ===

async def scrape_subreddit_http(
    subreddit_name: str,
    sort: str = "hot",
    limit: int = 25,
) -> list[dict]:
    """Scrape posts via Reddit's public .json endpoint with retry and 403 resilience."""
    data = await _fetch_subreddit_json(subreddit_name, sort=sort, limit=limit)
    posts = []

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
    logger.info("[Scraper] Using HTTP JSON mode with retry/403 resilience")

    all_posts = []
    for tier in tiers:
        subreddits = SUBREDDIT_TIERS.get(tier, [])
        for sub_name in subreddits:
            try:
                posts = await scrape_subreddit_http(sub_name, limit=limit_per_sub)
                all_posts.extend(posts)
                logger.info("[Scraper] r/%s: %d posts", sub_name, len(posts))
                await asyncio.sleep(2)  # rate limit between subreddits
            except Exception as e:
                # Graceful skip — log and continue, don't crash pipeline
                logger.error(
                    "[Scraper] All retries failed for r/%s, skipping: %s",
                    sub_name, e,
                )
                continue

    return all_posts
