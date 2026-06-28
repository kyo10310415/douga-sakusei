#!/bin/bash
# start.sh - 統合サービス起動スクリプト
# supervisord で API + Celery Worker + Celery Beat を1コンテナで管理
# Render Disk（/opt/render/project/src/uploads）をファイル共有に使用

set -e

echo "=== VTuber Studio Starting (Unified Container) ==="
echo "APP_ENV: ${APP_ENV:-development}"

# ── デフォルト値の設定 ──
export PORT="${PORT:-8000}"
export LOG_LEVEL="${LOG_LEVEL:-info}"

# ── アップロードディレクトリ確保 ──
# Render Disk がマウントされていれば /opt/render/project/src/uploads が永続化される
# マウントされていない場合は一時ディレクトリとして機能（開発環境用）
UPLOAD_PATH="${UPLOAD_DIR:-/opt/render/project/src/uploads}"
mkdir -p "${UPLOAD_PATH}"
mkdir -p "${UPLOAD_PATH}/voices"
mkdir -p "${UPLOAD_PATH}/videos"
mkdir -p "${UPLOAD_PATH}/assets"
mkdir -p "${UPLOAD_PATH}/defaults"
echo "Upload dir: ${UPLOAD_PATH}"

# supervisord のログディレクトリを作成
mkdir -p /var/log/supervisor
mkdir -p /var/run

# ── DBマイグレーション実行 ──
echo "=== Running DB migrations ==="
cd /app
alembic upgrade head
echo "=== Migrations complete ==="

# ── supervisord でプロセス一括起動 ──
# uvicorn（API） + celery worker + celery beat
echo "=== Starting supervisord (API + Worker + Beat) ==="
exec supervisord -c /etc/supervisor/conf.d/vtuber.conf
