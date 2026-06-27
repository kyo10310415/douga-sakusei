"""Add voice_instructions column to character_profiles

gpt-4o-mini-tts の instructions パラメータでしゃべり方スタイルを
指定できるようにするためのカラム追加。

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-27 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "character_profiles",
        sa.Column("voice_instructions", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("character_profiles", "voice_instructions")
