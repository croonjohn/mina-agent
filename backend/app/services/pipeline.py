"""Pipeline orchestrator — runs the full scrape → analyze → generate flow."""
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PipelineRun, ScrapedPost, TrendAnalysis, ContentItem
from app.scrapers.reddit_scraper import scrape_tiers
from app.scrapers.itchio_scraper import scrape_all_itchio
from app.services.trend_analyzer import analyze_trends_with_claude, generate_content_with_claude


async def run_pipeline(
    db: AsyncSession,
    platforms: list[str] = None,
    tiers: list[int] = None,
    content_types: list[str] = None,
    auto_approve: bool = False,
) -> dict:
    """
    Execute the full pipeline: scrape → analyze → generate.
    Returns pipeline status dict with live updates.
    """
    if platforms is None:
        platforms = ["reddit", "itchio"]
    if tiers is None:
        tiers = [1, 2]
    if content_types is None:
        content_types = ["post", "comment"]

    # Create pipeline run record
    pipeline = PipelineRun(
        config={
            "platforms": platforms,
            "tiers": tiers,
            "content_types": content_types,
            "auto_approve": auto_approve,
        },
        status="running",
        steps={},
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)

    pipeline_id = pipeline.id
    steps = {}

    try:
        # === Step 1: Scrape ===
        steps["scrape"] = {"status": "running", "started_at": _now()}
        all_posts = []

        if "reddit" in platforms:
            reddit_posts = await scrape_tiers(tiers=tiers, limit_per_sub=25)
            all_posts.extend(reddit_posts)

        if "itchio" in platforms:
            itchio_posts = await scrape_all_itchio(limit_per_source=20)
            all_posts.extend(itchio_posts)

        # Save scraped posts to DB
        for post_data in all_posts:
            post = ScrapedPost(
                pipeline_id=pipeline_id,
                platform=post_data["platform"],
                source=post_data["source"],
                external_id=post_data["external_id"],
                title=post_data["title"],
                body=post_data.get("body"),
                author=post_data.get("author"),
                url=post_data.get("url"),
                score=post_data.get("score", 0),
                comment_count=post_data.get("comment_count", 0),
                metadata_=post_data.get("metadata", {}),
            )
            db.add(post)

        await db.commit()
        steps["scrape"] = {"status": "completed", "count": len(all_posts), "started_at": steps["scrape"]["started_at"], "completed_at": _now()}

        # === Step 2: Analyze ===
        steps["analyze"] = {"status": "running", "started_at": _now()}

        analysis_result = await analyze_trends_with_claude(all_posts)

        trend = TrendAnalysis(
            pipeline_id=pipeline_id,
            topics=analysis_result.get("topics", []),
            opportunities=analysis_result.get("opportunities", []),
            sentiment_summary=analysis_result.get("sentiment_summary", ""),
            raw_response=str(analysis_result),
        )
        db.add(trend)
        await db.commit()

        steps["analyze"] = {
            "status": "completed",
            "topics": len(analysis_result.get("topics", [])),
            "opportunities": len(analysis_result.get("opportunities", [])),
            "started_at": steps["analyze"]["started_at"],
            "completed_at": _now(),
        }

        # === Step 3: Generate Content ===
        steps["generate"] = {"status": "running", "started_at": _now()}
        generated_count = 0

        opportunities = analysis_result.get("opportunities", [])[:5]
        for opp in opportunities:
            content_result = await generate_content_with_claude(
                content_type=opp.get("opportunity_type", "post"),
                platform=opp.get("platform", "reddit"),
                target=opp.get("source", "gamedev"),
                trend_context=opp,
            )

            if "error" not in content_result:
                content_item = ContentItem(
                    pipeline_id=pipeline_id,
                    platform=content_result.get("platform", opp.get("platform", "reddit")),
                    target=content_result.get("target", opp.get("source", "")),
                    content_type=content_result.get("content_type", "post"),
                    title=content_result.get("title"),
                    body=content_result.get("body", ""),
                    trend_context=opp,
                    status="approved" if auto_approve else "pending",
                )
                db.add(content_item)
                generated_count += 1

        await db.commit()
        steps["generate"] = {
            "status": "completed",
            "count": generated_count,
            "started_at": steps["generate"]["started_at"],
            "completed_at": _now(),
        }

        # Update pipeline
        pipeline.status = "completed"
        pipeline.steps = steps
        pipeline.posts_scraped = len(all_posts)
        pipeline.contents_generated = generated_count
        pipeline.completed_at = datetime.now(timezone.utc)
        await db.commit()

        return {
            "pipeline_id": str(pipeline_id),
            "status": "completed",
            "steps": steps,
            "posts_scraped": len(all_posts),
            "contents_generated": generated_count,
        }

    except Exception as e:
        pipeline.status = "failed"
        pipeline.error = str(e)
        pipeline.steps = steps
        pipeline.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return {
            "pipeline_id": str(pipeline_id),
            "status": "failed",
            "error": str(e),
            "steps": steps,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
