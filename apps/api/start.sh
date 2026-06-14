#!/bin/bash
# Renderデプロイ時の起動スクリプト（無料プラン対応・all-in-one）
# 1. DBマイグレーション実行
# 2. Celery Worker をバックグラウンドで起動
# 3. Celery Beat  をバックグラウンドで起動
# 4. Uvicorn（API）をフォアグラウンドで起動

set -e

echo "=== VTuber Studio API Starting ==="
echo "APP_ENV: ${APP_ENV:-development}"

# アップロードディレクトリ作成
mkdir -p "${UPLOAD_DIR:-/tmp/uploads}"

# DBマイグレーション実行
echo "=== Running DB migrations ==="
cd /app
alembic upgrade head

# Celery Worker をバックグラウンド起動
echo "=== Starting Celery Worker ==="
celery -A app.jobs.celery_app worker \
    --loglevel=info \
    --concurrency=1 \
    -Q youtube,ai,video,upload,default \
    --logfile=/tmp/celery-worker.log &
WORKER_PID=$!
echo "Celery Worker PID: $WORKER_PID"

# Celery Beat をバックグラウンド起動
echo "=== Starting Celery Beat ==="
celery -A app.jobs.celery_app beat \
    --loglevel=info \
    --logfile=/tmp/celery-beat.log &
BEAT_PID=$!
echo "Celery Beat PID: $BEAT_PID"

# プロセス終了時のクリーンアップ
cleanup() {
    echo "=== Shutting down ==="
    kill $WORKER_PID $BEAT_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# Uvicorn をフォアグラウンドで起動（メインプロセス）
echo "=== Starting API server ==="
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1 \
    --log-level "${LOG_LEVEL:-info}"
