"""Align DB schema with current SQLAlchemy models

- youtube_accounts: add missing columns (channel_title, channel_description,
  subscriber_count, video_count, view_count, oauth_scopes, last_synced_at),
  rename channel_name→channel_title, rename scopes→oauth_scopes
- weekly_metrics: add missing columns to match WeeklyMetrics model
- video_metrics: create table (VideoMetrics model)
- character_profiles: create table (CharacterProfile model)
- character_images: create table (CharacterImage model)
- video_theme_settings: create table (VideoThemeSetting model)
- video_plans: create table (VideoPlan model)
- scripts: create table (Script model)
- script_sections: create table (ScriptSection model)
- generated_voices: create table (GeneratedVoice model)
- generated_assets: create table (GeneratedAsset model)
- render_jobs: create table (RenderJob model)
- generated_videos: create table (GeneratedVideo model)
- youtube_uploads: create table (YouTubeUpload model)
- review_checklists: create table (ReviewChecklist model)
- approvals: create table (Approval model)
- improvement_logs: create table (ImprovementLog model)
- system_settings: create table (SystemSetting model)
- job_logs: create table (JobLog model)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    from sqlalchemy import inspect
    bind = op.get_bind()
    return inspect(bind).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    from sqlalchemy import inspect, text
    bind = op.get_bind()
    result = bind.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table_name, "c": column_name})
    return result.fetchone() is not None


def upgrade() -> None:
    # ================================================================
    # youtube_accounts: カラム追加・リネーム
    # ================================================================
    # channel_name → channel_title (旧カラムが存在すればリネーム、なければ追加)
    if _column_exists('youtube_accounts', 'channel_name'):
        op.alter_column('youtube_accounts', 'channel_name', new_column_name='channel_title')
    elif not _column_exists('youtube_accounts', 'channel_title'):
        op.add_column('youtube_accounts', sa.Column('channel_title', sa.String(255), nullable=True))

    if not _column_exists('youtube_accounts', 'channel_description'):
        op.add_column('youtube_accounts', sa.Column('channel_description', sa.Text(), nullable=True))

    if not _column_exists('youtube_accounts', 'subscriber_count'):
        op.add_column('youtube_accounts', sa.Column('subscriber_count', sa.Integer(), nullable=True))

    if not _column_exists('youtube_accounts', 'video_count'):
        op.add_column('youtube_accounts', sa.Column('video_count', sa.Integer(), nullable=True))

    if not _column_exists('youtube_accounts', 'view_count'):
        op.add_column('youtube_accounts', sa.Column('view_count', sa.Integer(), nullable=True))

    # scopes → oauth_scopes
    if _column_exists('youtube_accounts', 'scopes'):
        op.alter_column('youtube_accounts', 'scopes', new_column_name='oauth_scopes')
    elif not _column_exists('youtube_accounts', 'oauth_scopes'):
        op.add_column('youtube_accounts', sa.Column('oauth_scopes', sa.JSON(), nullable=True))

    if not _column_exists('youtube_accounts', 'last_synced_at'):
        op.add_column('youtube_accounts', sa.Column('last_synced_at', sa.DateTime(), nullable=True))

    # ================================================================
    # weekly_metrics: カラム追加・リネーム
    # ================================================================
    # week_start → week_start_date
    if _column_exists('weekly_metrics', 'week_start'):
        op.alter_column('weekly_metrics', 'week_start', new_column_name='week_start_date')
    elif not _column_exists('weekly_metrics', 'week_start_date'):
        op.add_column('weekly_metrics', sa.Column('week_start_date', sa.Date(), nullable=True))

    # week_end → week_end_date
    if _column_exists('weekly_metrics', 'week_end'):
        op.alter_column('weekly_metrics', 'week_end', new_column_name='week_end_date')
    elif not _column_exists('weekly_metrics', 'week_end_date'):
        op.add_column('weekly_metrics', sa.Column('week_end_date', sa.Date(), nullable=True))

    for col, typ in [
        ('total_impressions', sa.Integer()),
        ('ctr', sa.Float()),
        ('avg_view_duration', sa.Float()),
        ('avg_view_percentage', sa.Float()),
        ('subscribers_gained', sa.Integer()),
        ('subscribers_lost', sa.Integer()),
        ('net_subscribers', sa.Integer()),
        ('total_shares', sa.Integer()),
        ('views_change_rate', sa.Float()),
        ('ctr_change_rate', sa.Float()),
        ('subscribers_change_rate', sa.Float()),
        ('raw_data', sa.JSON()),
    ]:
        if not _column_exists('weekly_metrics', col):
            op.add_column('weekly_metrics', sa.Column(col, typ, nullable=True))

    # ================================================================
    # video_metrics テーブル
    # ================================================================
    if not _table_exists('video_metrics'):
        op.create_table(
            'video_metrics',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('youtube_account_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('weekly_metrics_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('youtube_video_id', sa.String(50), nullable=False),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('published_at', sa.DateTime(), nullable=True),
            sa.Column('thumbnail_url', sa.String(500), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('category_id', sa.String(50), nullable=True),
            sa.Column('views', sa.Integer(), nullable=True, default=0),
            sa.Column('impressions', sa.Integer(), nullable=True, default=0),
            sa.Column('ctr', sa.Float(), nullable=True),
            sa.Column('avg_view_duration', sa.Float(), nullable=True),
            sa.Column('avg_view_percentage', sa.Float(), nullable=True),
            sa.Column('likes', sa.Integer(), nullable=True, default=0),
            sa.Column('comments', sa.Integer(), nullable=True, default=0),
            sa.Column('shares', sa.Integer(), nullable=True, default=0),
            sa.Column('subscribers_gained', sa.Integer(), nullable=True, default=0),
            sa.Column('views_change_rate', sa.Float(), nullable=True),
            sa.ForeignKeyConstraint(['youtube_account_id'], ['youtube_accounts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['weekly_metrics_id'], ['weekly_metrics.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_video_metrics_youtube_video_id', 'video_metrics', ['youtube_video_id'])

    # ================================================================
    # character_profiles テーブル
    # ================================================================
    if not _table_exists('character_profiles'):
        op.create_table(
            'character_profiles',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('personality', sa.Text(), nullable=True),
            sa.Column('speaking_style', sa.Text(), nullable=True),
            sa.Column('voice_provider', sa.String(50), nullable=True),
            sa.Column('voice_id', sa.String(100), nullable=True),
            sa.Column('voice_settings', sa.JSON(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # character_images テーブル
    # ================================================================
    if not _table_exists('character_images'):
        op.create_table(
            'character_images',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('character_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('image_type', sa.String(50), nullable=False),
            sa.Column('file_path', sa.String(500), nullable=True),
            sa.Column('file_url', sa.String(500), nullable=True),
            sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
            sa.ForeignKeyConstraint(['character_id'], ['character_profiles.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # video_theme_settings テーブル
    # ================================================================
    if not _table_exists('video_theme_settings'):
        op.create_table(
            'video_theme_settings',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('target_audience', sa.Text(), nullable=True),
            sa.Column('content_style', sa.String(100), nullable=True),
            sa.Column('bg_music_style', sa.String(100), nullable=True),
            sa.Column('color_scheme', sa.JSON(), nullable=True),
            sa.Column('font_style', sa.String(100), nullable=True),
            sa.Column('transition_style', sa.String(100), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # video_plans テーブル
    # ================================================================
    if not _table_exists('video_plans'):
        op.create_table(
            'video_plans',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('youtube_account_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('analysis_report_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('character_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('theme_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('goal', sa.Text(), nullable=True),
            sa.Column('target_audience', sa.Text(), nullable=True),
            sa.Column('total_duration_seconds', sa.Integer(), nullable=True, default=600),
            sa.Column('structure', sa.JSON(), nullable=True),
            sa.Column('youtube_title_candidates', sa.JSON(), nullable=True),
            sa.Column('youtube_description', sa.Text(), nullable=True),
            sa.Column('youtube_tags', sa.JSON(), nullable=True),
            sa.Column('youtube_category_id', sa.String(50), nullable=True),
            sa.Column('thumbnail_policy', sa.Text(), nullable=True),
            sa.Column('pinned_comment', sa.Text(), nullable=True),
            sa.Column('cta', sa.Text(), nullable=True),
            sa.Column('status', sa.String(50), nullable=True, default='draft'),
            sa.ForeignKeyConstraint(['youtube_account_id'], ['youtube_accounts.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['analysis_report_id'], ['ai_analysis_reports.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['character_id'], ['character_profiles.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['theme_id'], ['video_theme_settings.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # scripts テーブル
    # ================================================================
    if not _table_exists('scripts'):
        op.create_table(
            'scripts',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('video_plan_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('character_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('hook_text', sa.Text(), nullable=True),
            sa.Column('full_script', sa.Text(), nullable=True),
            sa.Column('subtitle_text', sa.Text(), nullable=True),
            sa.Column('asset_list', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(50), nullable=True, default='draft'),
            sa.ForeignKeyConstraint(['video_plan_id'], ['video_plans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['character_id'], ['character_profiles.id'], ondelete='SET NULL'),
            sa.UniqueConstraint('video_plan_id'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # script_sections テーブル
    # ================================================================
    if not _table_exists('script_sections'):
        op.create_table(
            'script_sections',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('script_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('order_index', sa.Integer(), nullable=False),
            sa.Column('section_type', sa.String(50), nullable=False),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.Column('narration', sa.Text(), nullable=True),
            sa.Column('subtitle', sa.Text(), nullable=True),
            sa.Column('direction', sa.Text(), nullable=True),
            sa.Column('expression', sa.String(50), nullable=True, default='normal'),
            sa.Column('background_image_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('asset_ids', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # render_jobs テーブル
    # ================================================================
    if not _table_exists('render_jobs'):
        op.create_table(
            'render_jobs',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('video_plan_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('status', sa.String(50), nullable=True, default='pending'),
            sa.Column('progress_percent', sa.Integer(), nullable=True, default=0),
            sa.Column('current_step', sa.String(100), nullable=True),
            sa.Column('output_file_path', sa.String(500), nullable=True),
            sa.Column('output_file_url', sa.String(500), nullable=True),
            sa.Column('output_duration_seconds', sa.Float(), nullable=True),
            sa.Column('output_file_size', sa.Integer(), nullable=True),
            sa.Column('render_log', sa.Text(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('celery_task_id', sa.String(255), nullable=True),
            sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
            sa.Column('max_retries', sa.Integer(), nullable=True, default=3),
            sa.ForeignKeyConstraint(['video_plan_id'], ['video_plans.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # generated_voices テーブル
    # ================================================================
    if not _table_exists('generated_voices'):
        op.create_table(
            'generated_voices',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('section_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('character_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('tts_provider', sa.String(50), nullable=True),
            sa.Column('voice_id', sa.String(100), nullable=True),
            sa.Column('speech_rate', sa.Float(), nullable=True, default=1.0),
            sa.Column('pitch', sa.Float(), nullable=True, default=0.0),
            sa.Column('emotion_strength', sa.Float(), nullable=True, default=0.7),
            sa.Column('file_path', sa.String(500), nullable=True),
            sa.Column('file_url', sa.String(500), nullable=True),
            sa.Column('duration_seconds', sa.Float(), nullable=True),
            sa.Column('file_size', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(50), nullable=True, default='pending'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('generated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['section_id'], ['script_sections.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['character_id'], ['character_profiles.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # generated_assets テーブル
    # ================================================================
    if not _table_exists('generated_assets'):
        op.create_table(
            'generated_assets',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('section_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('render_job_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('asset_type', sa.String(50), nullable=False),
            sa.Column('prompt', sa.Text(), nullable=True),
            sa.Column('provider', sa.String(50), nullable=True),
            sa.Column('external_id', sa.String(255), nullable=True),
            sa.Column('file_path', sa.String(500), nullable=True),
            sa.Column('file_url', sa.String(500), nullable=True),
            sa.Column('original_filename', sa.String(255), nullable=True),
            sa.Column('mime_type', sa.String(100), nullable=True),
            sa.Column('file_size', sa.Integer(), nullable=True),
            sa.Column('width', sa.Integer(), nullable=True),
            sa.Column('height', sa.Integer(), nullable=True),
            sa.Column('duration_seconds', sa.Float(), nullable=True),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(50), nullable=True, default='pending'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['section_id'], ['script_sections.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['render_job_id'], ['render_jobs.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # generated_videos テーブル
    # ================================================================
    if not _table_exists('generated_videos'):
        op.create_table(
            'generated_videos',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('render_job_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('video_plan_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('thumbnail_path', sa.String(500), nullable=True),
            sa.Column('thumbnail_url', sa.String(500), nullable=True),
            sa.Column('file_path', sa.String(500), nullable=True),
            sa.Column('file_url', sa.String(500), nullable=True),
            sa.Column('duration_seconds', sa.Float(), nullable=True),
            sa.Column('resolution', sa.String(50), nullable=True, default='1920x1080'),
            sa.Column('file_size', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['render_job_id'], ['render_jobs.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['video_plan_id'], ['video_plans.id'], ondelete='SET NULL'),
            sa.UniqueConstraint('render_job_id'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # youtube_uploads テーブル
    # ================================================================
    if not _table_exists('youtube_uploads'):
        op.create_table(
            'youtube_uploads',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('generated_video_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('youtube_account_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('youtube_video_id', sa.String(100), nullable=True),
            sa.Column('youtube_url', sa.String(500), nullable=True),
            sa.Column('upload_status', sa.String(50), nullable=True, default='pending'),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('category_id', sa.String(50), nullable=True),
            sa.Column('thumbnail_uploaded', sa.Boolean(), nullable=True, default=False),
            sa.Column('privacy_status', sa.String(50), nullable=True, default='unlisted'),
            sa.Column('published_at', sa.DateTime(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('uploaded_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['generated_video_id'], ['generated_videos.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['youtube_account_id'], ['youtube_accounts.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('generated_video_id'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # review_checklists テーブル
    # ================================================================
    if not _table_exists('review_checklists'):
        op.create_table(
            'review_checklists',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('generated_video_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('no_factual_errors', sa.Boolean(), nullable=True),
            sa.Column('no_inappropriate_content', sa.Boolean(), nullable=True),
            sa.Column('matches_character', sa.Boolean(), nullable=True),
            sa.Column('video_coherent', sa.Boolean(), nullable=True),
            sa.Column('voice_ok', sa.Boolean(), nullable=True),
            sa.Column('subtitle_ok', sa.Boolean(), nullable=True),
            sa.Column('revision_request', sa.Text(), nullable=True),
            sa.Column('reviewer_notes', sa.Text(), nullable=True),
            sa.Column('checked_at', sa.DateTime(), nullable=True),
            sa.Column('checked_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(['generated_video_id'], ['generated_videos.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['checked_by'], ['users.id'], ondelete='SET NULL'),
            sa.UniqueConstraint('generated_video_id'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # approvals テーブル
    # ================================================================
    if not _table_exists('approvals'):
        op.create_table(
            'approvals',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('youtube_upload_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('status', sa.String(50), nullable=True, default='pending'),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('rejected_at', sa.DateTime(), nullable=True),
            sa.Column('reject_reason', sa.Text(), nullable=True),
            sa.Column('published_at', sa.DateTime(), nullable=True),
            sa.Column('published_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(['youtube_upload_id'], ['youtube_uploads.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['published_by'], ['users.id'], ondelete='SET NULL'),
            sa.UniqueConstraint('youtube_upload_id'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # improvement_logs テーブル
    # ================================================================
    if not _table_exists('improvement_logs'):
        op.create_table(
            'improvement_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('youtube_account_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('video_plan_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('youtube_upload_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('log_type', sa.String(50), nullable=False),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('actual_views', sa.Integer(), nullable=True),
            sa.Column('actual_ctr', sa.Float(), nullable=True),
            sa.Column('actual_retention', sa.Float(), nullable=True),
            sa.Column('actual_subscribers_gained', sa.Integer(), nullable=True),
            sa.Column('ai_analysis', sa.Text(), nullable=True),
            sa.Column('improvement_suggestions', sa.JSON(), nullable=True),
            sa.Column('applied_to_next', sa.Boolean(), nullable=True, default=False),
            sa.Column('applied_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['youtube_account_id'], ['youtube_accounts.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['video_plan_id'], ['video_plans.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['youtube_upload_id'], ['youtube_uploads.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # system_settings テーブル
    # ================================================================
    if not _table_exists('system_settings'):
        op.create_table(
            'system_settings',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('key', sa.String(255), nullable=False),
            sa.Column('value', sa.Text(), nullable=True),
            sa.Column('value_json', sa.JSON(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_sensitive', sa.Boolean(), nullable=True, default=False),
            sa.UniqueConstraint('key'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # job_logs テーブル
    # ================================================================
    if not _table_exists('job_logs'):
        op.create_table(
            'job_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('render_job_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('job_type', sa.String(100), nullable=False),
            sa.Column('task_id', sa.String(255), nullable=True),
            sa.Column('status', sa.String(50), nullable=False),
            sa.Column('message', sa.Text(), nullable=True),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('error_traceback', sa.Text(), nullable=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('action', sa.String(100), nullable=True),
            sa.Column('resource_type', sa.String(100), nullable=True),
            sa.Column('resource_id', sa.String(255), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('duration_seconds', sa.Float(), nullable=True),
            sa.ForeignKeyConstraint(['render_job_id'], ['render_jobs.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade() -> None:
    # 追加したものを逆順で削除
    for tbl in [
        'job_logs', 'system_settings', 'improvement_logs',
        'approvals', 'review_checklists', 'youtube_uploads',
        'generated_videos', 'generated_assets', 'generated_voices',
        'render_jobs', 'script_sections', 'scripts', 'video_plans',
        'video_theme_settings', 'character_images', 'character_profiles',
        'video_metrics',
    ]:
        if _table_exists(tbl):
            op.drop_table(tbl)
