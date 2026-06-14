#!/bin/bash
# Renderデプロイ時の起動スクリプト
# 1. DBマイグレーションを実行
# 2. Uvicornでサーバー起動

set -e

echo "=== VTuber Studio API Starting ==="
echo "APP_ENV: ${APP_ENV:-development}"

# アップロードディレクトリ作成
mkdir -p "${UPLOAD_DIR:-/tmp/uploads}"

# DBマイグレーション実行
echo "=== Running DB migrations ==="
cd /app
alembic upgrade head

echo "=== Starting API server ==="
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}" \
    --log-level "${LOG_LEVEL:-info}"
