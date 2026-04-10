"""Pipeline orchestrator — runs the full scrape -> analyze -> generate flow."""
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PipelineRun, ScrapedPost, TrendAnalysis, ContentItem
from app.scrapers.reddit_scraper import scrape_tiers
from app.scrapers.itchio_scraper import scrape_all_itchio
from app.services.trend_analyzer import analyze_trends_with_claude, generate_content_with_claude

logger = logging.getLogger(__name__)


async def _commit_step(db: AsyncSession, pipeline_id, steps: dict):
    """Commit the current steps state to DB so the frontend can poll for progress."""
    await db.execute(
        update(PipelineRun)
        .where(PipelineRun.id == pipeline_id)
        .values(steps=steps)
    )
    await db.commit()


async def run_pipeline(
    db: AsyncSession,
    platforms: list[str] = None,
    tiers: list[int] = None,
    content_types: list[str] = None,
    auto_approve: bool = False,
) -> dict:
    """
    Execute the full pipeline: scrape -> analyze -> generate.
    Commits step progress to DB after each step starts and completes
    so the frontend can poll /pipeline/status/{id} for live updates.
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
        # === Step 1: Scrape — START ===
        steps["scrape"] = {"status": "running", "started_at": _now()}
        await _commit_step(db, pipeline_id, steps)
        logger.info("[Pipeline %s] scrape-start", pipeline_id)

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

        # === Step 1: Scrape — DONE ===
        steps["scrape"] = {
            "status": "completed",
            "count": len(all_posts),
            "started_at": steps["scrape"]["started_at"],
            "completed_at": _now(),
        }
        await _commit_step(db, pipeline_id, steps)
        logger.info("[Pipeline %s] scrape-done (%d posts)", pipeline_id, len(all_posts))

        # === Step 2: Analyze — START ===
        steps["analyze"] = {"status": "running", "started_at": _now()}
        await _commit_step(db, pipeline_id, steps)
        logger.info("[Pipeline %s] analyze-start", pipeline_id)

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

        # === Step 2: Analyze — DONE ===
        steps["analyze"] = {
            "status": "completed",
            "topics": len(analysis_result.get("topics", [])),
            "opportunities": len(analysis_result.get("opportunities", [])),
            "started_at": steps["analyze"]["started_at"],
            "completed_at": _now(),
        }
        await _commit_step(db, pipeline_id, steps)
        logger.info("[Pipeline %s] analyze-done", pipeline_id)

        # === Step 3: Generate Content — START ===
        steps["generate"] = {"status": "running", "started_at": _now()}
        await _commit_step(db, pipeline_id, steps)
        logger.info("[Pipeline %s] generate-start", pipeline_id)

        generated_count = 0

        opportunities = analysis_result.get("opportunities", [])[:5]

        # Cross-reference opportunity post_titles with ScrapedPost records
        # to inject real URLs and external_ids
        for opp in opportunities:
            post_title = opp.get("post_title", "")
            if post_title:
                match_result = await db.execute(
                    select(ScrapedPost)
                    .where(ScrapedPost.pipeline_id == pipeline_id)
                    .where(ScrapedPost.title == post_title)
                    .limit(1)
                )
                matched_post = match_result.scalar_one_or_none()
                if matched_post:
                    opp["post_url"] = matched_post.url or ""
                    opp["post_external_id"] = matched_post.external_id or ""

        for opp in opportunities:
            opp_type = opp.get("opportunity_type", "post")

            content_result = await generate_content_with_claude(
                content_type=opp_type,
                platform=opp.get("platform", "reddit"),
                target=opp.get("source", "gamedev"),
                trend_context=opp,
            )

            if "error" not in content_result:
                # For comments, target must be the Reddit post external_id (e.g. t3_abc123)
                # so Devvit knows which post to comment on
                if opp_type == "comment" and opp.get("post_external_id"):
                    target = opp["post_external_id"]
                else:
                    target = content_result.get("target", opp.get("source", ""))

                content_item = ContentItem(
                    pipeline_id=pipeline_id,
                    platform=content_result.get("platform", opp.get("platform", "reddit")),
                    target=target,
                    content_type=content_result.get("content_type", "post"),
                    title=content_result.get("title"),
                    body=content_result.get("body", ""),
                    trend_context=opp,
                    source_post_url=opp.get("post_url", ""),
                    status="approved" if auto_approve else "pending",
                )
                db.add(content_item)
                generated_count += 1

        await db.commit()

        # === Step 3: Generate — DONE ===
        steps["generate"] = {
            "status": "completed",
            "count": generated_count,
            "started_at": steps["generate"]["started_at"],
            "completed_at": _now(),
        }
        await _commit_step(db, pipeline_id, steps)
        logger.info("[Pipeline %s] generate-done (%d items)", pipeline_id, generated_count)

        # Update pipeline as completed
        await db.execute(
            update(PipelineRun)
            .where(PipelineRun.id == pipeline_id)
            .values(
                status="completed",
                steps=steps,
                posts_scraped=len(all_posts),
                contents_generated=generated_count,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

        return {
            "pipeline_id": str(pipeline_id),
            "status": "completed",
            "steps": steps,
            "posts_scraped": len(all_posts),
            "contents_generated": generated_count,
        }

    except Exception as e:
        logger.error("[Pipeline %s] failed: %s", pipeline_id, e)
        steps["_error"] = str(e)
        await db.execute(
            update(PipelineRun)
            .where(PipelineRun.id == pipeline_id)
            .values(
                status="failed",
                error=str(e),
                steps=steps,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        return {
            "pipeline_id": str(pipeline_id),
            "status": "failed",
            "error": str(e),
            "steps": steps,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
