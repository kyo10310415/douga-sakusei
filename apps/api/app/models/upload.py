from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class YouTubeUpload(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "youtube_uploads"

    generated_video_id = Column(UUID(as_uuid=True), ForeignKey("generated_videos.id"), nullable=False, unique=True)
    youtube_account_id = Column(UUID(as_uuid=True), ForeignKey("youtube_accounts.id"), nullable=False)

    youtube_video_id = Column(String(100), nullable=True)
    youtube_url = Column(String(500), nullable=True)
    upload_status = Column(String(50), default="pending")
    # pending | uploading | unlisted | published | failed

    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    category_id = Column(String(50), nullable=True)
    thumbnail_uploaded = Column(Boolean, default=False)

    # 公開状態
    privacy_status = Column(String(50), default="unlisted")  # unlisted | public | private
    published_at = Column(DateTime, nullable=True)

    # エラー
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, nullable=True)

    generated_video = relationship("GeneratedVideo", back_populates="youtube_upload")
    approval = relationship("Approval", back_populates="youtube_upload", uselist=False)


class ReviewChecklist(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_checklists"

    generated_video_id = Column(UUID(as_uuid=True), ForeignKey("generated_videos.id"), nullable=False, unique=True)

    # チェック項目 (True = OK)
    no_factual_errors = Column(Boolean, nullable=True)  # 事実誤認がない
    no_inappropriate_content = Column(Boolean, nullable=True)  # 不適切表現がない
    matches_character = Column(Boolean, nullable=True)  # キャラクター設定に合っている
    video_coherent = Column(Boolean, nullable=True)  # 動画として破綻していない
    voice_ok = Column(Boolean, nullable=True)  # 音声が問題ない
    subtitle_ok = Column(Boolean, nullable=True)  # 字幕が問題ない

    # 修正依頼
    revision_request = Column(Text, nullable=True)
    reviewer_notes = Column(Text, nullable=True)

    checked_at = Column(DateTime, nullable=True)
    checked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    generated_video = relationship("GeneratedVideo", back_populates="review_checklist")


class Approval(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approvals"

    youtube_upload_id = Column(UUID(as_uuid=True), ForeignKey("youtube_uploads.id"), nullable=False, unique=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    status = Column(String(50), default="pending")  # pending | approved | rejected
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    reject_reason = Column(Text, nullable=True)

    # 公開後の情報
    published_at = Column(DateTime, nullable=True)
    published_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    youtube_upload = relationship("YouTubeUpload", back_populates="approval")
