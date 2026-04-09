import uuid
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text, JSON, Enum, Float, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config = Column(JSON, default={})
    status = Column(String(20), default="running")  # running | completed | failed
    steps = Column(JSON, default={})
    error = Column(Text, nullable=True)
    posts_scraped = Column(Integer, default=0)
    contents_generated = Column(Integer, default=0)
    contents_published = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ScrapedPost(Base):
    __tablename__ = "scraped_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(20), index=True)  # reddit | itchio
    source = Column(String(100))  # subreddit name or board name
    external_id = Column(String(500))
    title = Column(Text)
    body = Column(Text, nullable=True)
    author = Column(String(100), nullable=True)
    url = Column(Text, nullable=True)
    score = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, default={})
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=True)


class TrendAnalysis(Base):
    __tablename__ = "trend_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=True)
    topics = Column(JSON, default=[])
    opportunities = Column(JSON, default=[])
    sentiment_summary = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())


class ContentItem(Base):
    __tablename__ = "content_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=True)
    platform = Column(String(20))  # reddit | itchio
    target = Column(String(100))  # subreddit or board
    content_type = Column(String(50))  # post | comment | devlog
    title = Column(Text, nullable=True)
    body = Column(Text)
    image_url = Column(Text, nullable=True)
    template_id = Column(String(50), nullable=True)
    trend_context = Column(JSON, nullable=True)
    status = Column(String(20), default="pending", index=True)  # pending|approved|rejected|published
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)


class PublishedPost(Base):
    __tablename__ = "published_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_id = Column(Integer, ForeignKey("content_queue.id"))
    platform = Column(String(20))
    external_url = Column(Text, nullable=True)
    external_id = Column(String(100), nullable=True)
    score = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    metrics = Column(JSON, default={})
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    last_checked_at = Column(DateTime(timezone=True), nullable=True)


class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    published_post_id = Column(Integer, ForeignKey("published_posts.id"), nullable=True)
    level = Column(Integer, default=2)  # 1-5
    trigger_type = Column(String(50))
    description = Column(Text)
    ai_draft_response = Column(Text, nullable=True)
    status = Column(String(20), default="open", index=True)  # open|resolved|dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class Template(Base):
    __tablename__ = "templates"

    id = Column(String(50), primary_key=True)
    name = Column(String(200))
    platform = Column(String(20))
    content_type = Column(String(50))
    template_text = Column(Text)
    variables = Column(JSON, default=[])
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ToneGuideline(Base):
    __tablename__ = "tone_guidelines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    use_words = Column(JSON, default=[])
    avoid_words = Column(JSON, default=[])
    principles = Column(JSON, default=[])
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_title = Column(String(300))
    game_url = Column(Text, nullable=True)
    game_description = Column(Text, nullable=True)
    target_platforms = Column(JSON, default=["reddit"])
    target_communities = Column(JSON, default=[])
    extra_context = Column(JSON, default={})
    callback_url = Column(Text, nullable=True)
    status = Column(String(30), default="pending", index=True)  # pending|analyzing|generating|ready|publishing|completed|failed
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=True)
    content_ids = Column(JSON, default=[])
    result_summary = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    requested_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text)
    events = Column(JSON, default=[])  # content.generated, content.published, promotion.completed, etc.
    secret = Column(String(200), nullable=True)
    owner = Column(String(100), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
