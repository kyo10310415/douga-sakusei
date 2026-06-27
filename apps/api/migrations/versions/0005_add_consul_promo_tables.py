"""Add consul promo tables (content_projects, posts, creative_assets,
analytics, ai_generations, prompt_templates)

These tables support the VTuber consul promotional content management system:
- content_projects: campaign/project grouping
- posts: generated social media posts (X/Instagram/TikTok/YouTube Shorts)
- creative_assets: image prompts, video scripts, thumbnails per post
- post_analytics: impressions/likes/etc per post
- promo_ai_generations: AI generation history for promo content
- prompt_templates: reusable prompt templates + initial seed data

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-15 13:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    from sqlalchemy import inspect
    bind = op.get_bind()
    return inspect(bind).has_table(table_name)


def upgrade() -> None:
    # ================================================================
    # content_projects
    # ================================================================
    if not _table_exists('content_projects'):
        op.create_table(
            'content_projects',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            # ターゲット層: beginner / 0_1000 / 1000_10000
            sa.Column('target_segment', sa.String(50), nullable=True),
            # 目的: awareness / consult / line / document / achievement / knowhow
            sa.Column('goal', sa.String(50), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # posts
    # ================================================================
    if not _table_exists('posts'):
        op.create_table(
            'posts',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
            # YouTube分析データとの連携
            sa.Column('weekly_metrics_id', postgresql.UUID(as_uuid=True), nullable=True),
            # 媒体: x / instagram / tiktok / youtube_shorts
            sa.Column('platform', sa.String(50), nullable=False),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('body', sa.Text(), nullable=True),
            sa.Column('caption', sa.Text(), nullable=True),
            sa.Column('hashtags', sa.JSON(), nullable=True),
            sa.Column('cta', sa.String(100), nullable=True),
            # ターゲット層
            sa.Column('target_segment', sa.String(50), nullable=True),
            # 投稿目的
            sa.Column('goal', sa.String(50), nullable=True),
            # トーン: gentle / professional / provocative / beginner / business
            sa.Column('tone', sa.String(50), nullable=True),
            # ステータス: draft/pending_review/approved/scheduled/published/rejected
            sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
            sa.Column('scheduled_at', sa.DateTime(), nullable=True),
            sa.Column('published_at', sa.DateTime(), nullable=True),
            # X投稿後のtweet_id
            sa.Column('external_post_id', sa.String(255), nullable=True),
            sa.Column('external_post_url', sa.String(500), nullable=True),
            sa.Column('memo', sa.Text(), nullable=True),
            # 禁止表現チェック結果
            sa.Column('ng_check_passed', sa.Boolean(), nullable=True),
            sa.Column('ng_check_details', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['content_projects.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['weekly_metrics_id'], ['weekly_metrics.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_posts_platform', 'posts', ['platform'])
        op.create_index('ix_posts_status', 'posts', ['status'])
        op.create_index('ix_posts_user_id', 'posts', ['user_id'])

    # ================================================================
    # creative_assets
    # ================================================================
    if not _table_exists('creative_assets'):
        op.create_table(
            'creative_assets',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
            # asset_type: image_prompt/image/video_script/video/thumbnail_prompt/audio_script
            sa.Column('asset_type', sa.String(50), nullable=False),
            sa.Column('prompt', sa.Text(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('file_url', sa.String(500), nullable=True),
            sa.Column('metadata', sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # post_analytics
    # ================================================================
    if not _table_exists('post_analytics'):
        op.create_table(
            'post_analytics',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column('impressions', sa.Integer(), nullable=True),
            sa.Column('likes', sa.Integer(), nullable=True),
            sa.Column('comments', sa.Integer(), nullable=True),
            sa.Column('shares', sa.Integer(), nullable=True),
            sa.Column('saves', sa.Integer(), nullable=True),
            sa.Column('profile_clicks', sa.Integer(), nullable=True),
            sa.Column('url_clicks', sa.Integer(), nullable=True),
            sa.Column('leads', sa.Integer(), nullable=True),        # 無料相談申込
            sa.Column('conversions', sa.Integer(), nullable=True),  # 成約
            sa.Column('memo', sa.Text(), nullable=True),
            # AI分析結果
            sa.Column('ai_analysis', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # promo_ai_generations
    # ================================================================
    if not _table_exists('promo_ai_generations'):
        op.create_table(
            'promo_ai_generations',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            # generation_type: post/image_prompt/video_script/analysis/regenerate
            sa.Column('generation_type', sa.String(50), nullable=False),
            sa.Column('input_prompt', sa.Text(), nullable=True),
            sa.Column('output_text', sa.Text(), nullable=True),
            sa.Column('model', sa.String(100), nullable=True),
            sa.Column('prompt_tokens', sa.Integer(), nullable=True),
            sa.Column('completion_tokens', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )

    # ================================================================
    # prompt_templates
    # ================================================================
    if not _table_exists('prompt_templates'):
        op.create_table(
            'prompt_templates',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            # type: post_theme/cta/hashtag/ng_expression/tone
            sa.Column('type', sa.String(50), nullable=False),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('template_text', sa.Text(), nullable=True),
            sa.Column('platform', sa.String(50), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('sort_order', sa.Integer(), nullable=True, server_default='0'),
            sa.PrimaryKeyConstraint('id'),
        )

        # ── 初期テーマテンプレートをシード ──
        from sqlalchemy import text
        import uuid as _uuid
        from datetime import datetime as _dt

        now = _dt.utcnow()
        themes = [
            "新人VTuberが伸びない理由",
            "VTuberを始める前に決めるべきこと",
            "AIで効率化できるVTuber作業",
            "収益化までのロードマップ",
            "登録者1000人までにやること",
            "登録者1万人までに必要な運営視点",
            "伸びるVTuberのプロフィール設計",
            "初配信前チェックリスト",
            "配信企画の作り方",
            "X運用で失敗しやすいポイント",
            "YouTube導線の作り方",
            "ファン化につながる投稿設計",
            "AIを使ったサムネ・タイトル改善",
            "VTuber活動が続かない人の特徴",
            "収益化を目指すなら最初に整えるべき導線",
        ]
        ng_expressions = [
            "必ず収益化できます",
            "絶対に伸びます",
            "登録者が確実に増えます",
            "誰でも稼げます",
            "楽して稼げます",
            "放置で収益化",
            "成功保証",
        ]
        rows = []
        for i, theme in enumerate(themes):
            rows.append({
                "id": str(_uuid.uuid4()),
                "created_at": now,
                "updated_at": now,
                "type": "post_theme",
                "name": theme,
                "template_text": theme,
                "platform": None,
                "is_active": True,
                "sort_order": i,
            })
        for i, ng in enumerate(ng_expressions):
            rows.append({
                "id": str(_uuid.uuid4()),
                "created_at": now,
                "updated_at": now,
                "type": "ng_expression",
                "name": ng,
                "template_text": ng,
                "platform": None,
                "is_active": True,
                "sort_order": i,
            })
        bind = op.get_bind()
        for row in rows:
            bind.execute(text(
                "INSERT INTO prompt_templates "
                "(id,created_at,updated_at,type,name,template_text,platform,is_active,sort_order) "
                "VALUES (:id,:created_at,:updated_at,:type,:name,:template_text,"
                ":platform,:is_active,:sort_order)"
            ), row)


def downgrade() -> None:
    for tbl in ['promo_ai_generations', 'post_analytics', 'creative_assets',
                'posts', 'content_projects', 'prompt_templates']:
        if _table_exists(tbl):
            op.drop_table(tbl)
