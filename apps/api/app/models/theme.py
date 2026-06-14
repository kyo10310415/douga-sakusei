from sqlalchemy import (
    Column, String, Boolean, Text, ForeignKey, JSON, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, UUIDMixin


class VideoThemeSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "video_theme_settings"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False, default="デフォルト設定")
    main_channel_theme = Column(Text, nullable=True)  # メインチャンネルテーマ
    target_genres = Column(JSON, nullable=True)  # 扱うジャンル
    excluded_genres = Column(JSON, nullable=True)  # 扱わないジャンル
    target_audience = Column(Text, nullable=True)  # ターゲット視聴者

    # 動画の目的 (複数選択可)
    purposes = Column(JSON, nullable=True)
    # ["subscriber_growth", "view_growth", "product_funnel", "education", "fan_building"]

    default_duration_seconds = Column(Integer, default=600)  # デフォルト10分

    # 動画構成テンプレート
    structure_hook_seconds = Column(Integer, default=15)
    structure_problem_seconds = Column(Integer, default=60)
    structure_main_seconds = Column(Integer, default=420)
    structure_example_seconds = Column(Integer, default=60)
    structure_summary_seconds = Column(Integer, default=30)
    structure_cta_seconds = Column(Integer, default=15)
    custom_structure = Column(JSON, nullable=True)  # カスタム構成

    # 方針テンプレート
    thumbnail_policy = Column(Text, nullable=True)
    title_policy = Column(Text, nullable=True)
    description_template = Column(Text, nullable=True)
    pinned_comment_template = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
