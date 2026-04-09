"""Publisher module — queues Reddit content for Devvit, prepares itch.io for manual copy."""
from typing import Optional


def prepare_reddit_publish(
    target: str,
    title: str,
    body: str,
    content_type: str = "post",
    reply_to_url: str = None,
) -> dict:
    """
    Prepare Reddit content for publishing via Devvit.

    Instead of posting directly (PRAW is deprecated for new apps),
    content stays in the content_queue with status="approved".
    The Devvit app polls GET /api/v1/devvit/tasks and handles actual posting.

    This function returns publish metadata for the caller.
    """
    return {
        "platform": "reddit",
        "method": "devvit",
        "target": target,
        "content_type": content_type,
        "title": title,
        "body_preview": body[:200] if body else "",
        "status": "queued_for_devvit",
        "instructions": (
            "Content is approved and queued. "
            "The Devvit app will pick it up on the next scheduler cycle (every 5 minutes)."
        ),
    }


def prepare_itchio_content(title: str, body: str, board: str) -> dict:
    """
    Prepare itch.io content for manual posting (Copy-to-Clipboard in admin UI).
    No Playwright needed — admin copies and pastes manually.
    """
    board_urls = {
        "release-announcements": "https://itch.io/board/10022/release-announcements",
        "game-development": "https://itch.io/board/10020/game-development",
        "everything-else": "https://itch.io/board/10027/everything-else",
        "devlogs": "https://itch.io/dashboard/games",  # devlog is per-game
    }

    return {
        "platform": "itchio",
        "board": board,
        "board_url": board_urls.get(board, "https://itch.io/community"),
        "title": title,
        "body": body,
        "instructions": f"1. Open {board_urls.get(board, 'the board')}\n2. Click 'New Topic' or 'Post'\n3. Paste the title and body\n4. Submit",
        "ready_to_copy": True,
    }
