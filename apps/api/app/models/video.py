from sqlalchemy import (
    Column, String, Boolean, DateTime, Float, Integer,
    Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class VideoPlan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "video_plans"

    youtube_account_id = Column(UUID(as_uuid=True), ForeignKey("youtube_accounts.id"), nullable=True)
    analysis_report_id = Column(UUID(as_uuid=True), ForeignKey("ai_analysis_reports.id"), nullable=True)
    character_id = Column(UUID(as_uuid=True), ForeignKey("character_profiles.id"), nullable=True)
    theme_id = Column(UUID(as_uuid=True), ForeignKey("video_theme_settings.id"), nullable=True)

    title = Column(String(255), nullable=False)
    goal = Column(Text, nullable=True)  # 狙い
    target_audience = Column(Text, nullable=True)  # ターゲット・想定視聴者
    total_duration_seconds = Column(Integer, default=600)

    # 構成 (JSON: セクション名, 秒数, 説明)
    structure = Column(JSON, nullable=True)

    # YouTube メタ
    youtube_title_candidates = Column(JSON, nullable=True)  # タイトル案5つ
    youtube_description = Column(Text, nullable=True)
    youtube_tags = Column(JSON, nullable=True)
    youtube_category_id = Column(String(50), nullable=True)
    thumbnail_policy = Column(Text, nullable=True)
    pinned_comment = Column(Text, nullable=True)
    cta = Column(Text, nullable=True)

    status = Column(String(50), default="draft")  # draft | approved | archived

    script = relationship("Script", back_populates="video_plan", uselist=False)


class Script(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scripts"

    video_plan_id = Column(UUID(as_uuid=True), ForeignKey("video_plans.id"), nullable=False, unique=True)
    character_id = Column(UUID(as_uuid=True), ForeignKey("character_profiles.id"), nullable=True)

    hook_text = Column(Text, nullable=True)  # 冒頭15秒フック
    full_script = Column(Text, nullable=True)  # 全体台本
    subtitle_text = Column(Text, nullable=True)  # 字幕テキスト全体
    asset_list = Column(JSON, nullable=True)  # 必要な素材リスト

    status = Column(String(50), default="draft")  # draft | completed

    video_plan = relationship("VideoPlan", back_populates="script")
    sections = relationship("ScriptSection", back_populates="script", cascade="all, delete-orphan", order_by="ScriptSection.order_index")


class ScriptSection(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "script_sections"

    script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False)

    order_index = Column(Integer, nullable=False)
    section_type = Column(String(50), nullable=False)
    # hook | problem | main | example | summary | cta | custom

    title = Column(String(255), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    narration = Column(Text, nullable=True)  # キャラクターのセリフ
    subtitle = Column(Text, nullable=True)  # 字幕
    direction = Column(Text, nullable=True)  # 画面演出指示
    expression = Column(String(50), default="normal")
    # normal | smile | surprise | troubled | serious

    background_image_id = Column(UUID(as_uuid=True), nullable=True)
    asset_ids = Column(JSON, nullable=True)  # 使用する素材IDリスト

    script = relationship("Script", back_populates="sections")
    voices = relationship("GeneratedVoice", back_populates="section", cascade="all, delete-orphan")
    assets = relationship("GeneratedAsset", back_populates="section")


class GeneratedVoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "generated_voices"

    section_id = Column(UUID(as_uuid=True), ForeignKey("script_sections.id"), nullable=False)
    character_id = Column(UUID(as_uuid=True), ForeignKey("character_profiles.id"), nullable=True)

    text = Column(Text, nullable=False)  # 生成したテキスト
    tts_provider = Column(String(50), nullable=True)
    voice_id = Column(String(100), nullable=True)
    speech_rate = Column(Float, default=1.0)
    pitch = Column(Float, default=0.0)
    emotion_strength = Column(Float, default=0.7)

    file_path = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    file_size = Column(Integer, nullable=True)

    status = Column(String(50), default="pending")  # pending | generating | completed | failed
    error_message = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)

    section = relationship("ScriptSection", back_populates="voices")


class GeneratedAsset(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "generated_assets"

    section_id = Column(UUID(as_uuid=True), ForeignKey("script_sections.id"), nullable=True)
    render_job_id = Column(UUID(as_uuid=True), ForeignKey("render_jobs.id"), nullable=True)

    asset_type = Column(String(50), nullable=False)
    # background | insert_image | insert_video | bgm | se | thumbnail

    prompt = Column(Text, nullable=True)  # 生成プロンプト
    provider = Column(String(50), nullable=True)  # mock | openai | stability
    external_id = Column(String(255), nullable=True)

    file_path = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    metadata_ = Column("metadata", JSON, nullable=True)
    status = Column(String(50), default="pending")  # pending | generating | completed | failed
    error_message = Column(Text, nullable=True)

    section = relationship("ScriptSection", back_populates="assets")
    render_job = relationship("RenderJob", back_populates="assets", foreign_keys=[render_job_id])


class RenderJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "render_jobs"

    video_plan_id = Column(UUID(as_uuid=True), ForeignKey("video_plans.id"), nullable=False)

    status = Column(String(50), default="pending")
    # pending | analyzing | planning | scripting | generating_voice |
    # generating_assets | rendering | uploading | waiting_review |
    # approved | published | failed

    # 各ステップの進捗
    progress_percent = Column(Integer, default=0)
    current_step = Column(String(100), nullable=True)

    # 生成結果
    output_file_path = Column(String(500), nullable=True)
    output_file_url = Column(String(500), nullable=True)
    output_duration_seconds = Column(Float, nullable=True)
    output_file_size = Column(Integer, nullable=True)

    # ログ
    render_log = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # タイミング
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Celery
    celery_task_id = Column(String(255), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    generated_video = relationship("GeneratedVideo", back_populates="render_job", uselist=False)
    assets = relationship("GeneratedAsset", back_populates="render_job")


class GeneratedVideo(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "generated_videos"

    render_job_id = Column(UUID(as_uuid=True), ForeignKey("render_jobs.id"), nullable=False, unique=True)
    video_plan_id = Column(UUID(as_uuid=True), ForeignKey("video_plans.id"), nullable=True)

    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)

    file_path = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    resolution = Column(String(50), default="1920x1080")
    file_size = Column(Integer, nullable=True)

    render_job = relationship("RenderJob", back_populates="generated_video")
    youtube_upload = relationship("YouTubeUpload", back_populates="generated_video", uselist=False)
    review_checklist = relationship("ReviewChecklist", back_populates="generated_video", uselist=False)
