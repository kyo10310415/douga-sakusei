"""Add missing columns: custom_structure, voice_instructions

【背景】
モデルに定義済みだがマイグレーションに含まれていなかったカラムを追加する。

対象カラム：
1. video_theme_settings.custom_structure
   - モデル定義: Column(JSON, nullable=True)
   - 0004まで追加されておらずテーマ作成時に 500 エラーが発生していた

2. character_profiles.voice_instructions
   - 0006 で追加済みのはずだが念のため冪等（IF NOT EXISTS相当）で追加

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-28 10:00:00.000000
"""

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    # ── 1. video_theme_settings.custom_structure ──────────────────
    if not _column_exists("video_theme_settings", "custom_structure"):
        op.add_column(
            "video_theme_settings",
            sa.Column("custom_structure", sa.JSON(), nullable=True),
        )

    # ── 2. character_profiles.voice_instructions（0006の補完）──────
    if not _column_exists("character_profiles", "voice_instructions"):
        op.add_column(
            "character_profiles",
            sa.Column("voice_instructions", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("character_profiles", "voice_instructions"):
        op.drop_column("character_profiles", "voice_instructions")
    if _column_exists("video_theme_settings", "custom_structure"):
        op.drop_column("video_theme_settings", "custom_structure")
