"""Initial schema: all tables

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===========================================================
    # users テーブル
    # ===========================================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # ===========================================================
    # youtube_accounts テーブル
    # ===========================================================
    op.create_table(
        'youtube_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', sa.String(100), nullable=False),
        sa.Column('channel_name', sa.String(255), nullable=True),
        sa.Column('channel_thumbnail_url', sa.Text(), nullable=True),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_youtube_accounts_user_id', 'youtube_accounts', ['user_id'])
    op.create_index('ix_youtube_accounts_channel_id', 'youtube_accounts', ['channel_id'])

    # ===========================================================
    # weekly_metrics テーブル
    # ===========================================================
    op.create_table(
        'weekly_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('youtube_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('week_start', sa.DateTime(), nullable=False),
        sa.Column('week_end', sa.DateTime(), nullable=False),
        sa.Column('total_views', sa.Integer(), nullable=True, default=0),
        sa.Column('total_watch_time_minutes', sa.Integer(), nullable=True, default=0),
        sa.Column('average_view_duration', sa.Integer(), nullable=True, default=0),
        sa.Column('total_subscribers_gained', sa.Integer(), nullable=True, default=0),
        sa.Column('total_subscribers_lost', sa.Integer(), nullable=True, default=0),
        sa.Column('total_likes', sa.Integer(), nullable=True, default=0),
        sa.Column('total_comments', sa.Integer(), nullable=True, default=0),
        sa.Column('total_shares', sa.Integer(), nullable=True, default=0),
        sa.Column('average_ctr', sa.Float(), nullable=True, default=0.0),
        sa.Column('average_retention_rate', sa.Float(), nullable=True, default=0.0),
        sa.Column('video_metrics_json', sa.JSON(), nullable=True),
        sa.Column('raw_analytics_json', sa.JSON(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['youtube_account_id'], ['youtube_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_weekly_metrics_youtube_account_id', 'weekly_metrics', ['youtube_account_id'])
    op.create_index('ix_weekly_metrics_week_start', 'weekly_metrics', ['week_start'])

    # ===========================================================
    # characters テーブル (VTuberキャラクター)
    # ===========================================================
    op.create_table(
        'characters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('personality', sa.Text(), nullable=True),
        sa.Column('speaking_style', sa.Text(), nullable=True),
        sa.Column('avatar_image_url', sa.Text(), nullable=True),
        sa.Column('voice_provider', sa.String(50), nullable=True, default='mock'),
        sa.Column('voice_id', sa.String(100), nullable=True),
        sa.Column('voice_settings', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_characters_user_id', 'characters', ['user_id'])

    # ===========================================================
    # themes テーブル (動画テーマ)
    # ===========================================================
    op.create_table(
        'themes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_audience', sa.String(255), nullable=True),
        sa.Column('content_type', sa.String(50), nullable=True, default='commentary'),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True, default=10),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_themes_user_id', 'themes', ['user_id'])

    # ===========================================================
    # ai_analysis_reports テーブル
    # ===========================================================
    op.create_table(
        'ai_analysis_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('youtube_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('weekly_metrics_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('analysis_type', sa.String(50), nullable=True, default='weekly'),
        sa.Column('status', sa.String(50), nullable=True, default='pending'),
        sa.Column('trending_video_patterns', sa.Text(), nullable=True),
        sa.Column('declining_video_patterns', sa.Text(), nullable=True),
        sa.Column('high_ctr_title_patterns', sa.Text(), nullable=True),
        sa.Column('high_retention_patterns', sa.Text(), nullable=True),
        sa.Column('drop_off_factors', sa.Text(), nullable=True),
        sa.Column('improvement_points', sa.Text(), nullable=True),
        sa.Column('next_theme_suggestions', sa.JSON(), nullable=True),
        sa.Column('next_title_suggestions', sa.JSON(), nullable=True),
        sa.Column('next_thumbnail_suggestions', sa.JSON(), nullable=True),
        sa.Column('next_script_policy', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('ai_provider', sa.String(50), nullable=True),
        sa.Column('ai_model', sa.String(100), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['youtube_account_id'], ['youtube_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['weekly_metrics_id'], ['weekly_metrics.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_analysis_reports_youtube_account_id', 'ai_analysis_reports', ['youtube_account_id'])
    op.create_index('ix_ai_analysis_reports_status', 'ai_analysis_reports', ['status'])

    # ===========================================================
    # video_jobs テーブル
    # ===========================================================
    op.create_table(
        'video_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('youtube_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('analysis_report_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('character_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('theme_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=True, default='pending'),
        sa.Column('current_step', sa.String(100), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=True, default=0),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('script_content', sa.Text(), nullable=True),
        sa.Column('script_approved', sa.Boolean(), nullable=True, default=False),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('video_file_path', sa.Text(), nullable=True),
        sa.Column('video_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('youtube_video_id', sa.String(100), nullable=True),
        sa.Column('youtube_video_url', sa.Text(), nullable=True),
        sa.Column('upload_status', sa.String(50), nullable=True, default='not_uploaded'),
        sa.Column('visibility', sa.String(20), nullable=True, default='private'),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_step', sa.String(100), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['youtube_account_id'], ['youtube_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['analysis_report_id'], ['ai_analysis_reports.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_video_jobs_user_id', 'video_jobs', ['user_id'])
    op.create_index('ix_video_jobs_status', 'video_jobs', ['status'])

    # ===========================================================
    # video_reviews テーブル
    # ===========================================================
    op.create_table(
        'video_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('video_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('review_type', sa.String(50), nullable=True, default='final'),
        sa.Column('status', sa.String(50), nullable=True, default='pending'),
        sa.Column('approved', sa.Boolean(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['video_job_id'], ['video_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_video_reviews_video_job_id', 'video_reviews', ['video_job_id'])
    op.create_index('ix_video_reviews_status', 'video_reviews', ['status'])

    # ===========================================================
    # upload_records テーブル
    # ===========================================================
    op.create_table(
        'upload_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('video_job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('youtube_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('youtube_video_id', sa.String(100), nullable=True),
        sa.Column('upload_status', sa.String(50), nullable=True, default='pending'),
        sa.Column('visibility', sa.String(20), nullable=True, default='private'),
        sa.Column('scheduled_publish_at', sa.DateTime(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('upload_response_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['video_job_id'], ['video_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['youtube_account_id'], ['youtube_accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_upload_records_video_job_id', 'upload_records', ['video_job_id'])

    # ===========================================================
    # system_logs テーブル
    # ===========================================================
    op.create_table(
        'system_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('video_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('level', sa.String(20), nullable=True, default='info'),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['video_job_id'], ['video_jobs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_system_logs_level', 'system_logs', ['level'])
    op.create_index('ix_system_logs_category', 'system_logs', ['category'])


def downgrade() -> None:
    op.drop_table('system_logs')
    op.drop_table('upload_records')
    op.drop_table('video_reviews')
    op.drop_table('video_jobs')
    op.drop_table('ai_analysis_reports')
    op.drop_table('themes')
    op.drop_table('characters')
    op.drop_table('weekly_metrics')
    op.drop_table('youtube_accounts')
    op.drop_table('users')
