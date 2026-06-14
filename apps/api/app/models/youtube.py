import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Float, Integer,
    Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class YouTubeAccount(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "youtube_accounts"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    channel_id = Column(String(100), unique=True, nullable=False)
    channel_title = Column(String(255), nullable=True)
    channel_description = Column(Text, nullable=True)
    channel_thumbnail_url = Column(String(500), nullable=True)
    subscriber_count = Column(Integer, nullable=True)
    video_count = Column(Integer, nullable=True)
    view_count = Column(Integer, nullable=True)

    # OAuth tokens (encrypted)
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    oauth_scopes = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)

    # Relationships
    weekly_metrics = relationship("WeeklyMetrics", back_populates="youtube_account")
    video_metrics = relationship("VideoMetrics", back_populates="youtube_account")


class WeeklyMetrics(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "weekly_metrics"

    youtube_account_id = Column(UUID(as_uuid=True), ForeignKey("youtube_accounts.id"), nullable=False)
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)

    # 基本指標
    total_views = Column(Integer, default=0)
    total_impressions = Column(Integer, default=0)
    ctr = Column(Float, nullable=True)  # Click-through rate (%)
    avg_view_duration = Column(Float, nullable=True)  # seconds
    avg_view_percentage = Column(Float, nullable=True)  # %

    # 登録者
    subscribers_gained = Column(Integer, default=0)
    subscribers_lost = Column(Integer, default=0)
    net_subscribers = Column(Integer, default=0)

    # エンゲージメント
    total_likes = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)
    total_shares = Column(Integer, default=0)

    # 前週比
    views_change_rate = Column(Float, nullable=True)  # %
    ctr_change_rate = Column(Float, nullable=True)
    subscribers_change_rate = Column(Float, nullable=True)

    # 生データ (YouTube API レスポンス全体)
    raw_data = Column(JSON, nullable=True)

    youtube_account = relationship("YouTubeAccount", back_populates="weekly_metrics")
    video_metrics = relationship("VideoMetrics", back_populates="weekly_metrics")


class VideoMetrics(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "video_metrics"

    youtube_account_id = Column(UUID(as_uuid=True), ForeignKey("youtube_accounts.id"), nullable=False)
    weekly_metrics_id = Column(UUID(as_uuid=True), ForeignKey("weekly_metrics.id"), nullable=True)

    youtube_video_id = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    tags = Column(JSON, nullable=True)
    category_id = Column(String(50), nullable=True)

    # 指標
    views = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, nullable=True)
    avg_view_duration = Column(Float, nullable=True)
    avg_view_percentage = Column(Float, nullable=True)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    subscribers_gained = Column(Integer, default=0)

    # 前週比
    views_change_rate = Column(Float, nullable=True)

    youtube_account = relationship("YouTubeAccount", back_populates="video_metrics")
    weekly_metrics = relationship("WeeklyMetrics", back_populates="video_metrics")
