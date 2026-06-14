from sqlalchemy import (
    Column, String, Boolean, DateTime, Float, Integer,
    Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin, UUIDMixin


class ImprovementLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "improvement_logs"

    youtube_account_id = Column(UUID(as_uuid=True), ForeignKey("youtube_accounts.id"), nullable=True)
    video_plan_id = Column(UUID(as_uuid=True), ForeignKey("video_plans.id"), nullable=True)
    youtube_upload_id = Column(UUID(as_uuid=True), ForeignKey("youtube_uploads.id"), nullable=True)

    log_type = Column(String(50), nullable=False)  # performance | feedback | ai_suggestion
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)

    # 実績データ (公開後に取得)
    actual_views = Column(Integer, nullable=True)
    actual_ctr = Column(Float, nullable=True)
    actual_retention = Column(Float, nullable=True)
    actual_subscribers_gained = Column(Integer, nullable=True)

    # AI分析
    ai_analysis = Column(Text, nullable=True)
    improvement_suggestions = Column(JSON, nullable=True)

    applied_to_next = Column(Boolean, default=False)
    applied_at = Column(DateTime, nullable=True)


class SystemSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "system_settings"

    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    value_json = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    is_sensitive = Column(Boolean, default=False)  # センシティブ設定はマスク


class JobLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_logs"

    render_job_id = Column(UUID(as_uuid=True), ForeignKey("render_jobs.id"), nullable=True)
    job_type = Column(String(100), nullable=False)  # fetch_weekly | ai_analysis | render | upload | etc.
    task_id = Column(String(255), nullable=True)  # Celery task ID

    status = Column(String(50), nullable=False)  # started | success | failed | retrying
    message = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    error_traceback = Column(Text, nullable=True)

    # 操作ログ (セキュリティ)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=True)  # approve | publish | regenerate | delete
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
