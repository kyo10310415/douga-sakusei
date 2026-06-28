#!/bin/bash
# API サービス起動スクリプト（有料プラン対応・Worker分離版）
# 1. DBマイグレーション実行
# 2. Uvicorn（API）をフォアグラウンドで起動
# ※ Celery Worker/Beat は別サービス（Dockerfile.worker / Dockerfile.beat）で起動

set -e

echo "=== VTuber Studio API Starting ==="
echo "APP_ENV: ${APP_ENV:-development}"

# アップロード一時ディレクトリ作成
mkdir -p "${UPLOAD_DIR:-/tmp/uploads}"

# DBマイグレーション実行
echo "=== Running DB migrations ==="
cd /app
alembic upgrade head

# Uvicorn をフォアグラウンドで起動（メインプロセス）
echo "=== Starting API server ==="
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 \
    --log-level "${LOG_LEVEL:-info}"
