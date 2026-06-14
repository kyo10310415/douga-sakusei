"""Add missing columns to users table

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-02 00:00:00.000000

初期マイグレーション(0001)のusersテーブルに
display_name -> username へのカラム名修正と
is_admin, last_login_at カラムを追加する
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # display_name → username にリネーム（0001では display_name で作成済み）
    # ただし既にusernameが存在する場合はスキップ
    conn = op.get_bind()

    # カラム存在チェック用ヘルパー
    def column_exists(table, column):
        result = conn.execute(sa.text(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name='{table}' AND column_name='{column}'"
        ))
        return result.fetchone() is not None

    # display_name が存在して username がない場合 → リネーム
    if column_exists('users', 'display_name') and not column_exists('users', 'username'):
        op.alter_column('users', 'display_name', new_column_name='username')

    # username カラムがまだない場合 → 追加
    if not column_exists('users', 'username'):
        op.add_column('users', sa.Column('username', sa.String(100), nullable=True))
        # 既存データのusernameをemailの@前で埋める
        op.execute(sa.text(
            "UPDATE users SET username = split_part(email, '@', 1) WHERE username IS NULL"
        ))
        op.alter_column('users', 'username', nullable=False)

    # is_admin カラム追加
    if not column_exists('users', 'is_admin'):
        op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))

    # last_login_at カラム追加
    if not column_exists('users', 'last_login_at'):
        op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))

    # is_superuser が残っている場合は is_admin にマージして削除
    if column_exists('users', 'is_superuser') and column_exists('users', 'is_admin'):
        op.execute(sa.text(
            "UPDATE users SET is_admin = true WHERE is_superuser = true"
        ))
        op.drop_column('users', 'is_superuser')


def downgrade() -> None:
    conn = op.get_bind()

    def column_exists(table, column):
        result = conn.execute(sa.text(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name='{table}' AND column_name='{column}'"
        ))
        return result.fetchone() is not None

    if column_exists('users', 'last_login_at'):
        op.drop_column('users', 'last_login_at')
    if column_exists('users', 'is_admin'):
        op.drop_column('users', 'is_admin')
    if column_exists('users', 'username'):
        op.alter_column('users', 'username', new_column_name='display_name')
