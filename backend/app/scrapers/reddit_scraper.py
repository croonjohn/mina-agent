"""Reddit scraper - dual mode: PRAW (if API keys) or HTTP JSON (no keys needed)."""
import asyncpraw
import httpx
from typing import Optional

from app.core.config import get_settings

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


# === PRAW mode (needs API key, required for posting) ===

async def create_reddit_client() -> Optional[asyncpraw.Reddit]:
    """Create an authenticated Reddit client. Returns None if no credentials."""
    settings = get_settings()
    if not settings.reddit_client_id:
        return None

    return asyncpraw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        username=settings.reddit_username,
        password=settings.reddit_password,
        user_agent=settings.reddit_user_agent,
    )


async def scrape_subreddit_praw(
    reddit: asyncpraw.Reddit,
    subreddit_name: str,
    sort: str = "hot",
    limit: int = 25,
) -> list[dict]:
    """Scrape posts using PRAW (authenticated)."""
    posts = []
    subreddit = await reddit.subreddit(subreddit_name)

    if sort == "hot":
        submissions = subreddit.hot(limit=limit)
    elif sort == "new":
        submissions = subreddit.new(limit=limit)
    elif sort == "rising":
        submissions = subreddit.rising(limit=limit)
    else:
        submissions = subreddit.hot(limit=limit)

    async for submission in submissions:
        if submission.stickied:
            continue

        posts.append({
            "platform": "reddit",
            "source": subreddit_name,
            "external_id": submission.id,
            "title": submission.title,
            "body": submission.selftext[:2000] if submission.selftext else None,
            "author": str(submission.author) if submission.author else "[deleted]",
            "url": f"https://reddit.com{submission.permalink}",
            "score": submission.score,
            "comment_count": submission.num_comments,
            "metadata": {
                "flair": submission.link_flair_text,
                "created_utc": submission.created_utc,
                "is_self": submission.is_self,
                "subreddit": subreddit_name,
                "upvote_ratio": submission.upvote_ratio,
            },
        })

    return posts


# === Main entry point - auto-selects mode ===

async def scrape_tiers(tiers: list[int], limit_per_sub: int = 25) -> list[dict]:
    """Scrape subreddits. Uses PRAW if API keys exist, otherwise HTTP JSON."""
    settings = get_settings()
    use_praw = bool(settings.reddit_client_id)

    reddit = None
    if use_praw:
        reddit = await create_reddit_client()
        print("[Scraper] Using PRAW (authenticated mode)")
    else:
        print("[Scraper] Using HTTP JSON (no API key - read-only mode)")

    all_posts = []
    try:
        for tier in tiers:
            subreddits = SUBREDDIT_TIERS.get(tier, [])
            for sub_name in subreddits:
                try:
                    if use_praw and reddit:
                        posts = await scrape_subreddit_praw(reddit, sub_name, limit=limit_per_sub)
                    else:
                        posts = await scrape_subreddit_http(sub_name, limit=limit_per_sub)
                    all_posts.extend(posts)
                    print(f"[Scraper] r/{sub_name}: {len(posts)} posts")
                except Exception as e:
                    print(f"[Scraper] Error scraping r/{sub_name}: {e}")
                    continue
    finally:
        if reddit:
            await reddit.close()

    return all_posts
