"""Promotion service - game studios submit, Mina handles everything."""
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Promotion, ContentItem
from app.services.trend_analyzer import analyze_trends_with_claude, generate_content_with_claude
from app.services.webhook import fire_event, fire_callback
from app.scrapers.reddit_scraper import scrape_tiers

logger = logging.getLogger(__name__)

# Map community names to subreddit tiers for scraping context
COMMUNITY_TO_TIER = {
    "gamedev": 1, "indiegaming": 1, "IndieDev": 1, "itchio": 1, "WebGames": 1,
    "gamejams": 2, "playmygame": 2, "DestroyMyGame": 2, "gamedesign": 2,
    "gaming": 5, "Games": 5, "SideProject": 5,
}

DEFAULT_COMMUNITIES = ["gamedev", "indiegaming", "IndieDev", "WebGames", "playmygame"]


async def run_promotion(db: AsyncSession, promotion: Promotion):
    """
    Full promotion flow:
    1. Scrape target communities for trend context
    2. Generate tailored promotional content for each community
    3. Queue content for approval
    4. Notify via webhook at each step
    """
    promo_id = str(promotion.id)
    callback_url = promotion.callback_url
    communities = promotion.target_communities or DEFAULT_COMMUNITIES

    try:
        # === Step 1: Analyze current trends in target communities ===
        promotion.status = "analyzing"
        await db.commit()
        await _notify(db, callback_url, "promotion.analyzing", {
            "promotion_id": promo_id,
            "message": f"Analyzing trends in {len(communities)} communities...",
        })

        # Figure out which tiers to scrape
        tiers_needed = set()
        for c in communities:
            tier = COMMUNITY_TO_TIER.get(c, 1)
            tiers_needed.add(tier)

        posts = await scrape_tiers(tiers=list(tiers_needed), limit_per_sub=15)
        logger.info("[Promotion %s] Scraped %d posts for context", promo_id, len(posts))

        # Run trend analysis
        analysis = await analyze_trends_with_claude(posts)
        if "error" in analysis:
            logger.warning("[Promotion %s] Analysis returned error: %s", promo_id, analysis["error"])

        # === Step 2: Generate content for each target community ===
        promotion.status = "generating"
        await db.commit()
        await _notify(db, callback_url, "promotion.generating", {
            "promotion_id": promo_id,
            "message": f"Generating content for {len(communities)} communities...",
        })

        game_context = {
            "game_title": promotion.game_title,
            "game_url": promotion.game_url,
            "game_description": promotion.game_description,
            "extra": promotion.extra_context,
            "trend_topics": [t.get("keyword") for t in analysis.get("topics", [])[:5]],
            "community_sentiment": analysis.get("sentiment_summary", ""),
        }

        content_ids = []
        for community in communities:
            platform = "itchio" if community in ("itchio", "itch.io") else "reddit"
            content_type = "post" if community in ("playmygame", "WebGames", "DestroyMyGame") else "comment"

            result = await generate_content_with_claude(
                content_type=content_type,
                platform=platform,
                target=community,
                trend_context=game_context,
            )

            if "error" not in result:
                item = ContentItem(
                    platform=platform,
                    target=community,
                    content_type=result.get("content_type", content_type),
                    title=result.get("title"),
                    body=result.get("body", ""),
                    trend_context=game_context,
                    status="pending",
                )
                db.add(item)
                await db.flush()
                content_ids.append(item.id)
                logger.info("[Promotion %s] Generated content #%d for %s/%s", promo_id, item.id, platform, community)
            else:
                logger.warning("[Promotion %s] Failed to generate for %s: %s", promo_id, community, result["error"])

        await db.commit()

        # === Step 3: Mark promotion as ready ===
        promotion.status = "ready"
        promotion.content_ids = content_ids
        promotion.result_summary = f"Generated {len(content_ids)} content items for {len(communities)} communities."
        promotion.completed_at = datetime.now(timezone.utc)
        await db.commit()

        await _notify(db, callback_url, "promotion.ready", {
            "promotion_id": promo_id,
            "content_ids": content_ids,
            "count": len(content_ids),
            "message": promotion.result_summary,
            "review_url": f"/content?promotion={promo_id}",
        })

        # Also fire global webhook event
        await fire_event(db, "content.generated", {
            "promotion_id": promo_id,
            "content_ids": content_ids,
        })

        return promotion

    except Exception as e:
        promotion.status = "failed"
        promotion.error = str(e)
        promotion.completed_at = datetime.now(timezone.utc)
        await db.commit()

        await _notify(db, callback_url, "promotion.failed", {
            "promotion_id": promo_id,
            "error": str(e),
        })
        raise


async def _notify(db: AsyncSession, callback_url: str | None, event: str, payload: dict):
    """Send webhook + direct callback if URL provided."""
    await fire_event(db, event, payload)
    if callback_url:
        await fire_callback(callback_url, event, payload)
