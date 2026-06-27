"""
コンサル宣伝システム用 SQLAlchemy モデル
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer,
    Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class ContentProject(Base, UUIDMixin, TimestampMixin):
    """宣伝コンテンツプロジェクト（キャンペーン単位）"""
    __tablename__ = "content_projects"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # beginner / 0_1000 / 1000_10000
    target_segment = Column(String(50), nullable=True)
    # awareness / consult / line / document / achievement / knowhow
    goal = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    posts = relationship("Post", back_populates="project")


class Post(Base, UUIDMixin, TimestampMixin):
    """生成された投稿"""
    __tablename__ = "posts"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("content_projects.id"), nullable=True)
    # YouTube分析データとの連携
    weekly_metrics_id = Column(UUID(as_uuid=True), ForeignKey("weekly_metrics.id"), nullable=True)

    # x / instagram / tiktok / youtube_shorts
    platform = Column(String(50), nullable=False)
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)
    hashtags = Column(JSON, nullable=True)
    cta = Column(String(100), nullable=True)
    target_segment = Column(String(50), nullable=True)
    goal = Column(String(50), nullable=True)
    # gentle / professional / provocative / beginner / business
    tone = Column(String(50), nullable=True)

    # draft / pending_review / approved / scheduled / published / rejected
    status = Column(String(50), default="draft", nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)

    external_post_id = Column(String(255), nullable=True)   # X tweet_id など
    external_post_url = Column(String(500), nullable=True)
    memo = Column(Text, nullable=True)
    ng_check_passed = Column(Boolean, nullable=True)
    ng_check_details = Column(JSON, nullable=True)

    project = relationship("ContentProject", back_populates="posts")
    assets = relationship("CreativeAsset", back_populates="post", cascade="all, delete-orphan")
    analytics = relationship("PostAnalytics", back_populates="post", uselist=False,
                             cascade="all, delete-orphan")
    ai_generations = relationship("PromoAIGeneration", back_populates="post",
                                  cascade="all, delete-orphan")


class CreativeAsset(Base, UUIDMixin, TimestampMixin):
    """投稿に紐づく素材（画像プロンプト・動画台本など）"""
    __tablename__ = "creative_assets"

    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    # image_prompt / image / video_script / video / thumbnail_prompt / audio_script
    asset_type = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    metadata = Column(JSON, nullable=True)

    post = relationship("Post", back_populates="assets")


class PostAnalytics(Base, UUIDMixin, TimestampMixin):
    """投稿分析数値（手入力 or API取得）"""
    __tablename__ = "post_analytics"

    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, unique=True)
    impressions = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    shares = Column(Integer, nullable=True)
    saves = Column(Integer, nullable=True)
    profile_clicks = Column(Integer, nullable=True)
    url_clicks = Column(Integer, nullable=True)
    leads = Column(Integer, nullable=True)        # 無料相談申込数
    conversions = Column(Integer, nullable=True)  # 成約数
    memo = Column(Text, nullable=True)
    ai_analysis = Column(Text, nullable=True)

    post = relationship("Post", back_populates="analytics")


class PromoAIGeneration(Base, UUIDMixin, TimestampMixin):
    """宣伝コンテンツのAI生成履歴"""
    __tablename__ = "promo_ai_generations"

    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # post / image_prompt / video_script / analysis / regenerate
    generation_type = Column(String(50), nullable=False)
    input_prompt = Column(Text, nullable=True)
    output_text = Column(Text, nullable=True)
    model = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)

    post = relationship("Post", back_populates="ai_generations")


class PromptTemplate(Base, UUIDMixin, TimestampMixin):
    """プロンプトテンプレート（テーマ・CTA・NG表現など）"""
    __tablename__ = "prompt_templates"

    # post_theme / cta / hashtag / ng_expression / tone
    type = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    template_text = Column(Text, nullable=True)
    platform = Column(String(50), nullable=True)  # 媒体絞り込み用（None=全媒体）
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=True)
