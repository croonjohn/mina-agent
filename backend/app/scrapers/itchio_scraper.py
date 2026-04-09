"""itch.io scraper using HTTP requests + BeautifulSoup (read-only)."""
import httpx
from bs4 import BeautifulSoup
from typing import Optional


ITCHIO_BOARDS = {
    "release-announcements": "https://itch.io/board/10022/release-announcements",
    "game-development": "https://itch.io/board/10020/game-development",
    "everything-else": "https://itch.io/board/10027/everything-else",
}

ITCHIO_FEEDS = {
    "devlogs": "https://itch.io/devlogs",
    "top-games": "https://itch.io/games/top-rated",
    "new-games": "https://itch.io/games/newest",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}


async def scrape_board(board_key: str, limit: int = 20) -> list[dict]:
    """Scrape posts from an itch.io community board."""
    url = ITCHIO_BOARDS.get(board_key)
    if not url:
        return []

    posts = []
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(url, timeout=30)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    topics = soup.select(".topic_row")[:limit]

    for topic in topics:
        title_el = topic.select_one(".topic_title a")
        author_el = topic.select_one(".topic_author a")
        replies_el = topic.select_one(".topic_replies")

        if not title_el:
            continue

        posts.append({
            "platform": "itchio",
            "source": board_key,
            "external_id": title_el.get("href", ""),
            "title": title_el.get_text(strip=True),
            "body": None,
            "author": author_el.get_text(strip=True) if author_el else None,
            "url": f"https://itch.io{title_el['href']}" if title_el.get("href", "").startswith("/") else title_el.get("href", ""),
            "score": 0,
            "comment_count": int(replies_el.get_text(strip=True)) if replies_el else 0,
            "metadata": {"board": board_key},
        })

    return posts


async def scrape_devlogs(limit: int = 20) -> list[dict]:
    """Scrape recent devlog posts from itch.io."""
    posts = []
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        resp = await client.get(ITCHIO_FEEDS["devlogs"], timeout=30)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    entries = soup.select(".devlog_post")[:limit]

    for entry in entries:
        title_el = entry.select_one(".devlog_title a")
        author_el = entry.select_one(".game_author a")
        summary_el = entry.select_one(".devlog_summary")

        if not title_el:
            continue

        href = title_el.get("href", "")
        posts.append({
            "platform": "itchio",
            "source": "devlogs",
            "external_id": href,
            "title": title_el.get_text(strip=True),
            "body": summary_el.get_text(strip=True)[:500] if summary_el else None,
            "author": author_el.get_text(strip=True) if author_el else None,
            "url": href if href.startswith("http") else f"https://itch.io{href}",
            "score": 0,
            "comment_count": 0,
            "metadata": {"type": "devlog"},
        })

    return posts


async def scrape_all_itchio(limit_per_source: int = 20) -> list[dict]:
    """Scrape all configured itch.io sources."""
    all_posts = []

    for board_key in ITCHIO_BOARDS:
        try:
            posts = await scrape_board(board_key, limit=limit_per_source)
            all_posts.extend(posts)
        except Exception as e:
            print(f"[itch.io Scraper] Error scraping {board_key}: {e}")

    try:
        devlogs = await scrape_devlogs(limit=limit_per_source)
        all_posts.extend(devlogs)
    except Exception as e:
        print(f"[itch.io Scraper] Error scraping devlogs: {e}")

    return all_posts
