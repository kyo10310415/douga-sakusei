import asyncio
from datetime import datetime, timedelta, date
from typing import Optional
from app.jobs.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.youtube import YouTubeAccount, WeeklyMetrics, VideoMetrics
from app.models.log import JobLog
from app.services.youtube_service import youtube_service
from app.core.security import decrypt_token


@celery_app.task(
    bind=True,
    name="app.jobs.youtube_jobs.fetch_weekly_youtube_metrics",
    max_retries=3,
    default_retry_delay=300,
)
def fetch_weekly_youtube_metrics(self, youtube_account_id: Optional[str] = None):
    """週次YouTubeデータを取得してDBに保存"""
    db = SessionLocal()
    job_log = None

    try:
        # ジョブログ開始
        job_log = JobLog(
            job_type="fetch_weekly_youtube_metrics",
            task_id=self.request.id,
            status="started",
            message="YouTube週次データ取得開始",
            started_at=datetime.utcnow(),
        )
        db.add(job_log)
        db.commit()

        # 対象アカウントを取得
        if youtube_account_id:
            accounts = db.query(YouTubeAccount).filter(
                YouTubeAccount.id == youtube_account_id,
                YouTubeAccount.is_active == True,
            ).all()
        else:
            accounts = db.query(YouTubeAccount).filter(
                YouTubeAccount.is_active == True
            ).all()

        if not accounts:
            job_log.status = "success"
            job_log.message = "アクティブなYouTubeアカウントなし"
            job_log.finished_at = datetime.utcnow()
            db.commit()
            return {"status": "no_accounts"}

        results = []
        for account in accounts:
            try:
                result = _sync_account_metrics(db, account)
                results.append(result)
            except Exception as e:
                results.append({"account_id": str(account.id), "error": str(e)})

        job_log.status = "success"
        job_log.message = f"{len(results)}アカウントのデータ取得完了"
        job_log.finished_at = datetime.utcnow()
        db.commit()

        # 次のジョブをキック
        from app.jobs.ai_jobs import run_ai_analysis
        run_ai_analysis.delay()

        return {"status": "success", "results": results}

    except Exception as exc:
        if job_log:
            job_log.status = "failed"
            job_log.message = str(exc)
            job_log.finished_at = datetime.utcnow()
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


def _sync_account_metrics(db, account: YouTubeAccount) -> dict:
    """1アカウントのメトリクスを同期"""
    if not account.access_token_encrypted:
        raise Exception("アクセストークンが設定されていません")

    access_token = decrypt_token(account.access_token_encrypted)
    refresh_token = decrypt_token(account.refresh_token_encrypted) if account.refresh_token_encrypted else None

    # 今週の期間
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # 月曜日
    week_end = today

    # 動画リスト取得
    videos = youtube_service.get_videos_list(
        access_token=access_token,
        refresh_token=refresh_token,
        max_results=50,
        published_after=(week_start - timedelta(days=30)).isoformat() + "T00:00:00Z",
    )

    # 週次メトリクス作成
    weekly = WeeklyMetrics(
        youtube_account_id=account.id,
        week_start_date=week_start,
        week_end_date=week_end,
    )
    db.add(weekly)
    db.flush()

    total_views = 0
    total_impressions = 0
    total_likes = 0
    total_comments = 0

    for video in videos:
        try:
            analytics = youtube_service.get_video_analytics(
                access_token=access_token,
                refresh_token=refresh_token,
                video_id=video["youtube_video_id"],
                start_date=week_start.isoformat(),
                end_date=week_end.isoformat(),
            )
        except Exception:
            analytics = {}

        # 動画メトリクス保存
        existing = db.query(VideoMetrics).filter(
            VideoMetrics.youtube_video_id == video["youtube_video_id"],
            VideoMetrics.youtube_account_id == account.id,
        ).first()

        if not existing:
            vm = VideoMetrics(
                youtube_account_id=account.id,
                weekly_metrics_id=weekly.id,
                youtube_video_id=video["youtube_video_id"],
                title=video.get("title"),
                description=video.get("description"),
                thumbnail_url=video.get("thumbnail_url"),
                tags=video.get("tags", []),
                **analytics,
            )
            db.add(vm)
        else:
            for key, val in analytics.items():
                setattr(existing, key, val)
            existing.weekly_metrics_id = weekly.id

        total_views += analytics.get("views", 0)
        total_impressions += analytics.get("impressions", 0)
        total_likes += analytics.get("likes", 0)
        total_comments += analytics.get("comments", 0)

    # 週次サマリー更新
    weekly.total_views = total_views
    weekly.total_impressions = total_impressions
    weekly.total_likes = total_likes
    weekly.total_comments = total_comments
    if total_impressions > 0:
        weekly.ctr = total_views / total_impressions * 100

    # 前週比計算
    prev_weekly = db.query(WeeklyMetrics).filter(
        WeeklyMetrics.youtube_account_id == account.id,
        WeeklyMetrics.week_start_date < week_start,
    ).order_by(WeeklyMetrics.week_start_date.desc()).first()

    if prev_weekly and prev_weekly.total_views > 0:
        weekly.views_change_rate = (total_views - prev_weekly.total_views) / prev_weekly.total_views * 100

    account.last_synced_at = datetime.utcnow()
    db.commit()

    return {"account_id": str(account.id), "videos_synced": len(videos)}
