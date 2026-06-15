"""Fix character_profiles and video_theme_settings columns to match models

- character_profiles: add missing columns (age_setting, tone, first_person,
  viewer_address, specialty_genres, weak_genres, character_description,
  ng_expressions, speech_samples, tts_provider, voice_type, speech_rate,
  pitch, emotion_strength, is_default)
  drop old mismatch columns (description, speaking_style, voice_provider,
  voice_id, voice_settings)
- character_images: add missing columns (original_filename, mime_type, file_size)
  drop old is_default column (not in current model)
- video_theme_settings: add missing columns (main_channel_theme, target_genres,
  excluded_genres, purposes, default_duration_seconds,
  structure_hook_seconds, structure_problem_seconds, structure_main_seconds,
  structure_example_seconds, structure_summary_seconds, structure_cta_seconds,
  thumbnail_policy, title_policy, description_template,
  pinned_comment_template, is_default)
  drop old mismatch columns (description, content_style, bg_music_style,
  color_scheme, font_style, transition_style)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-15 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    from sqlalchemy import text
    bind = op.get_bind()
    result = bind.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    ), {"t": table_name, "c": column_name})
    return result.fetchone() is not None


def upgrade() -> None:
    # ================================================================
    # character_profiles: 不要カラム削除 → 正しいカラム追加
    # ================================================================
    # 旧カラム削除（存在すれば）
    for col in ['description', 'speaking_style', 'voice_provider', 'voice_id', 'voice_settings']:
        if _column_exists('character_profiles', col):
            op.drop_column('character_profiles', col)

    # 新カラム追加
    new_char_cols = [
        ('age_setting',           sa.String(50),   True),
        ('tone',                  sa.Text(),        True),
        ('first_person',          sa.String(50),    True),
        ('viewer_address',        sa.String(50),    True),
        ('specialty_genres',      sa.JSON(),        True),
        ('weak_genres',           sa.JSON(),        True),
        ('character_description', sa.Text(),        True),
        ('ng_expressions',        sa.Text(),        True),
        ('speech_samples',        sa.Text(),        True),
        ('tts_provider',          sa.String(50),    True),
        ('voice_type',            sa.String(100),   True),
        ('speech_rate',           sa.Float(),       True),
        ('pitch',                 sa.Float(),       True),
        ('emotion_strength',      sa.Float(),       True),
        ('is_default',            sa.Boolean(),     True),
    ]
    for col_name, col_type, nullable in new_char_cols:
        if not _column_exists('character_profiles', col_name):
            op.add_column('character_profiles',
                sa.Column(col_name, col_type, nullable=nullable))

    # ================================================================
    # character_images: 不要カラム削除 → 必要カラム追加
    # ================================================================
    if _column_exists('character_images', 'is_default'):
        op.drop_column('character_images', 'is_default')

    for col_name, col_type in [
        ('original_filename', sa.String(255)),
        ('mime_type',         sa.String(100)),
        ('file_size',         sa.Integer()),
    ]:
        if not _column_exists('character_images', col_name):
            op.add_column('character_images',
                sa.Column(col_name, col_type, nullable=True))

    # ================================================================
    # video_theme_settings: 旧カラム削除 → 正しいカラム追加
    # ================================================================
    for col in ['description', 'content_style', 'bg_music_style',
                'color_scheme', 'font_style', 'transition_style']:
        if _column_exists('video_theme_settings', col):
            op.drop_column('video_theme_settings', col)

    new_theme_cols = [
        ('main_channel_theme',         sa.Text(),      True),
        ('target_genres',              sa.JSON(),      True),
        ('excluded_genres',            sa.JSON(),      True),
        ('purposes',                   sa.JSON(),      True),
        ('default_duration_seconds',   sa.Integer(),   True),
        ('structure_hook_seconds',     sa.Integer(),   True),
        ('structure_problem_seconds',  sa.Integer(),   True),
        ('structure_main_seconds',     sa.Integer(),   True),
        ('structure_example_seconds',  sa.Integer(),   True),
        ('structure_summary_seconds',  sa.Integer(),   True),
        ('structure_cta_seconds',      sa.Integer(),   True),
        ('thumbnail_policy',           sa.Text(),      True),
        ('title_policy',               sa.Text(),      True),
        ('description_template',       sa.Text(),      True),
        ('pinned_comment_template',    sa.Text(),      True),
        ('is_default',                 sa.Boolean(),   True),
    ]
    for col_name, col_type, nullable in new_theme_cols:
        if not _column_exists('video_theme_settings', col_name):
            op.add_column('video_theme_settings',
                sa.Column(col_name, col_type, nullable=nullable))


def downgrade() -> None:
    # character_profiles: 追加分を削除、旧カラムを戻す
    for col in ['age_setting', 'tone', 'first_person', 'viewer_address',
                'specialty_genres', 'weak_genres', 'character_description',
                'ng_expressions', 'speech_samples', 'tts_provider',
                'voice_type', 'speech_rate', 'pitch', 'emotion_strength', 'is_default']:
        if _column_exists('character_profiles', col):
            op.drop_column('character_profiles', col)

    # character_images: 追加分を削除
    for col in ['original_filename', 'mime_type', 'file_size']:
        if _column_exists('character_images', col):
            op.drop_column('character_images', col)

    # video_theme_settings: 追加分を削除
    for col in ['main_channel_theme', 'target_genres', 'excluded_genres',
                'purposes', 'default_duration_seconds',
                'structure_hook_seconds', 'structure_problem_seconds',
                'structure_main_seconds', 'structure_example_seconds',
                'structure_summary_seconds', 'structure_cta_seconds',
                'thumbnail_policy', 'title_policy', 'description_template',
                'pinned_comment_template', 'is_default']:
        if _column_exists('video_theme_settings', col):
            op.drop_column('video_theme_settings', col)
