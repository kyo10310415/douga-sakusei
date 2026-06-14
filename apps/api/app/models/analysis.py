from sqlalchemy import (
    Column, String, DateTime, Integer, Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class AIAnalysisReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_analysis_reports"

    youtube_account_id = Column(UUID(as_uuid=True), ForeignKey("youtube_accounts.id"), nullable=False)
    weekly_metrics_id = Column(UUID(as_uuid=True), ForeignKey("weekly_metrics.id"), nullable=True)

    analysis_type = Column(String(50), default="weekly")  # weekly | on_demand
    status = Column(String(50), default="pending")  # pending | running | completed | failed

    # 分析結果
    trending_video_patterns = Column(Text, nullable=True)  # 伸びた動画の共通点
    declining_video_patterns = Column(Text, nullable=True)  # 伸びなかった動画の共通点
    high_ctr_title_patterns = Column(Text, nullable=True)  # CTRが高いタイトル傾向
    high_retention_patterns = Column(Text, nullable=True)  # 視聴維持率が高い構成
    drop_off_factors = Column(Text, nullable=True)  # 離脱が起きやすい要素
    improvement_points = Column(Text, nullable=True)  # 次回改善点

    # 次回動画提案
    next_theme_suggestions = Column(JSON, nullable=True)  # テーマ案リスト
    next_title_suggestions = Column(JSON, nullable=True)  # タイトル案リスト
    next_thumbnail_suggestions = Column(JSON, nullable=True)  # サムネイル案
    next_script_policy = Column(Text, nullable=True)  # 台本方針

    # サマリー
    summary = Column(Text, nullable=True)  # AIによるサマリー

    # メタ
    ai_provider = Column(String(50), nullable=True)  # openai | mock
    ai_model = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)

    error_message = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
