"""Trend analysis using Claude Code CLI (Team Premium - $0 cost)."""
import asyncio
import json
import logging
import os
import shutil
import subprocess
from typing import Optional

from app.services.content_rules import CONTENT_RULES_PROMPT, validate_content

logger = logging.getLogger(__name__)


def _find_claude_cli() -> str:
    """Find the claude CLI binary path."""
    # Check env var first
    env_path = os.environ.get("CLAUDE_CLI_PATH")
    if env_path:
        return env_path
    found = shutil.which("claude")
    if found:
        return found
    # Docker/Linux: check common paths
    for p in ["/usr/local/bin/claude", "/usr/bin/claude"]:
        if os.path.isfile(p):
            return p
    # Windows npm global fallback
    if os.name == "nt":
        for base in [os.environ.get("APPDATA", ""), os.path.expanduser("~\\AppData\\Roaming")]:
            c = os.path.join(base, "npm", "claude.cmd")
            if os.path.isfile(c):
                return c
    return "claude"


async def analyze_trends_with_claude(posts: list[dict]) -> dict:
    """
    Call Claude Code CLI to analyze scraped posts for trends and opportunities.
    Uses Team Premium seat — no API cost.
    """
    # Prepare condensed post data (save tokens)
    condensed = []
    for p in posts[:100]:  # Limit to 100 most relevant
        condensed.append({
            "platform": p["platform"],
            "source": p["source"],
            "title": p["title"],
            "url": p.get("url", ""),
            "body": (p.get("body") or "")[:300],
            "score": p.get("score", 0),
            "comments": p.get("comment_count", 0),
        })

    prompt = f"""You are the Verse8 community manager AI "Mina". Analyze these scraped posts from Reddit and itch.io.

## Verse8 Context
- AI-native game creation platform (describe a game → AI builds it)
- HTML5 games (Phaser 2D, Three.js 3D), instant browser play
- 80/20 revenue split (creators get 80%)
- 5,000+ creators, 24,000+ games, 14M monthly visitors

## Scraped Posts (JSON)
{json.dumps(condensed, ensure_ascii=False)}

## Task
Return a JSON object with exactly this structure:
{{
  "topics": [
    {{"keyword": "...", "description": "why this is trending", "relevance_to_verse8": "high|medium|low", "post_count": N}}
  ],
  "opportunities": [
    {{"post_title": "...", "post_url": "...", "platform": "reddit|itchio", "source": "subreddit or board", "opportunity_type": "comment|post|showcase", "suggested_angle": "how Verse8 can contribute value here"}}
  ],
  "sentiment_summary": "1-2 sentence summary of community mood toward indie games and AI tools",
  "recommended_actions": ["action 1", "action 2", "action 3"]
}}

Return ONLY valid JSON, no markdown fences or explanation."""

    result = await _call_claude_code(prompt)
    if result:
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Try extracting JSON from response
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
            return {"error": "Failed to parse Claude response", "raw": result[:500]}

    return {"error": "Claude Code CLI call failed"}


async def generate_content_with_claude(
    content_type: str,
    platform: str,
    target: str,
    trend_context: dict,
    template: str = "",
    tone_guidelines: dict = None,
) -> dict:
    """Generate a post/comment using Claude Code CLI."""

    avoid_words = ""
    if tone_guidelines and tone_guidelines.get("avoid_words"):
        avoid_words = ", ".join(tone_guidelines["avoid_words"])
    else:
        avoid_words = "revolutionary, game-changer, disrupt, next-gen, cutting-edge, killer app, synergy, leverage, ecosystem, Web3, blockchain, NFT, metaverse, democratize, unlock, empower, 10x, 100x, no-code, AAA quality, limitless, magic, simply, just, best in class"

    prompt = f"""You are "Mina", a regular member of game dev communities who also happens to work at Verse8. Write a {content_type} for {platform} targeting {target}.

## Tone Rules (MUST follow)
- Write exactly like a real person on Reddit/itch.io forums. Short paragraphs, casual tone.
- You're a community member FIRST, not a marketer. Contribute to the discussion genuinely.
- Humble and honest. If Verse8 isn't the best fit, say so. Suggest alternatives too.
- Use contractions (don't, can't, it's). Never sound formal.

## CRITICAL RULES - DO NOT VIOLATE
- NEVER invent game titles, URLs, usernames, or content that doesn't exist.
- NEVER reference specific Verse8 games unless provided in trend context below.
- NEVER fabricate URLs like verse8.io/games/xxx. Only use verse8.io as the main URL.
- If no specific game data is given, only talk about the platform in general.
{CONTENT_RULES_PROMPT}
## NEVER use these words/phrases: {avoid_words}

## Verse8 facts (use sparingly, only when relevant):
- AI game creation platform - describe what you want, AI builds it
- HTML5 browser games (Phaser 2D, Three.js 3D)
- Creators keep 80% revenue
- Free to try at verse8.io

## Context for this post: {json.dumps(trend_context, ensure_ascii=False)}

## Template reference (adapt freely, don't copy): {template}

## Output
Return JSON: {{"title": "...", "body": "...", "content_type": "{content_type}", "platform": "{platform}", "target": "{target}"}}
For comments, title can be null. Return ONLY valid JSON."""

    result = await _call_claude_code(prompt)
    if result:
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(result[start:end])
            else:
                parsed = {"body": result, "title": None, "content_type": content_type, "platform": platform, "target": target}

        # Post-generation validation & auto-cleaning
        body = parsed.get("body", "")
        if body:
            validation = validate_content(body)
            parsed["body"] = validation["cleaned"]  # auto-fix em-dashes etc.
            parsed["content_rules_issues"] = validation["issues"]
            if not validation["valid"]:
                logger.warning(
                    "[Content Rules] Issues found: %s", validation["issues"]
                )

        return parsed

    return {"error": "Claude Code CLI call failed"}


async def _call_claude_code(prompt: str, timeout: int = 120) -> Optional[str]:
    """Execute Claude Code CLI as subprocess (Windows-compatible)."""
    def _run():
        cli = _find_claude_cli()
        use_shell = cli.endswith(".cmd")
        # Pass prompt via stdin to avoid Windows command-line length limit (WinError 206)
        # Use encoding='utf-8' to avoid cp949 UnicodeEncodeError on Korean Windows
        return subprocess.run(
            [cli, "-p", "--output-format", "text"],
            input=prompt,
            capture_output=True, text=True, timeout=timeout, shell=use_shell,
            encoding="utf-8",
        )
    try:
        logger.info("[Claude Code] Calling CLI: %s", _find_claude_cli())
        result = await asyncio.to_thread(_run)
        logger.info("[Claude Code] returncode=%d, stdout_len=%d, stderr_len=%d",
                     result.returncode, len(result.stdout), len(result.stderr))
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.error("[Claude Code] Error (code %d): %s", result.returncode, result.stderr[:500])
            return None
    except subprocess.TimeoutExpired:
        logger.error("[Claude Code] Timeout after %ds", timeout)
        return None
    except Exception as e:
        logger.error("[Claude Code] Exception (%s): %s", type(e).__name__, e)
        return None
