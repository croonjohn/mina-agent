"""Publisher module — prepares content for manual copy+paste publishing."""


def prepare_reddit_publish(
    target: str,
    title: str,
    body: str,
    content_type: str = "post",
    source_post_url: str = "",
) -> dict:
    """Prepare Reddit content for manual posting."""
    if content_type == "comment" and source_post_url:
        target_url = source_post_url
    else:
        target_url = f"https://www.reddit.com/r/{target}/submit?type=self"

    return {
        "platform": "reddit",
        "method": "manual_copy",
        "target": target,
        "target_url": target_url,
        "content_type": content_type,
        "title": title,
        "body": body,
        "instructions": f"1. Copy the content\n2. Open {target_url}\n3. Paste and submit",
    }


def prepare_itchio_content(title: str, body: str, board: str) -> dict:
    """Prepare itch.io content for manual posting."""
    board_urls = {
        "release-announcements": "https://itch.io/board/10022/release-announcements",
        "game-development": "https://itch.io/board/10020/game-development",
        "everything-else": "https://itch.io/board/10027/everything-else",
        "devlogs": "https://itch.io/dashboard/games",
    }

    target_url = board_urls.get(board, "https://itch.io/community")

    return {
        "platform": "itchio",
        "method": "manual_copy",
        "board": board,
        "target_url": target_url,
        "title": title,
        "body": body,
        "instructions": f"1. Copy the content\n2. Open {target_url}\n3. Click 'New Topic' or 'Post'\n4. Paste and submit",
    }
