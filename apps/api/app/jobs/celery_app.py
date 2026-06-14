from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "vtuber_studio",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.jobs.youtube_jobs",
        "app.jobs.ai_jobs",
        "app.jobs.video_jobs",
        "app.jobs.upload_jobs",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_max_retries=3,
    task_default_retry_delay=60,
    # タスクの結果を24時間保持
    result_expires=86400,
)

# 定期実行スケジュール（デフォルト: 毎週月曜日 9:00 JST）
# ダッシュボードからsystem_settingsで変更可能
celery_app.conf.beat_schedule = {
    "weekly-pipeline": {
        "task": "app.jobs.youtube_jobs.fetch_weekly_youtube_metrics",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),  # 毎週月曜日9時
        "options": {"queue": "weekly"},
    },
}
