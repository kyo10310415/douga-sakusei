from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.youtube import WeeklyMetrics, YouTubeAccount
from app.models.video import RenderJob, GeneratedVideo
from app.models.analysis import AIAnalysisReport
from app.models.upload import YouTubeUpload

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ダッシュボードのサマリーデータ"""
    # 最新の週次データ
    latest_metrics = db.query(WeeklyMetrics).order_by(
        WeeklyMetrics.week_start_date.desc()
    ).first()

    prev_metrics = None
    if latest_metrics:
        prev_metrics = db.query(WeeklyMetrics).filter(
            WeeklyMetrics.week_start_date < latest_metrics.week_start_date
        ).order_by(WeeklyMetrics.week_start_date.desc()).first()

    # 最新AI分析
    latest_analysis = db.query(AIAnalysisReport).filter(
        AIAnalysisReport.status == "completed"
    ).order_by(AIAnalysisReport.created_at.desc()).first()

    # 進行中のジョブ
    active_jobs = db.query(RenderJob).filter(
        RenderJob.status.notin_(["failed", "published", "approved"])
    ).order_by(RenderJob.created_at.desc()).limit(5).all()

    # レビュー待ち動画
    waiting_review = db.query(RenderJob).filter(
        RenderJob.status == "waiting_review"
    ).count()

    # YouTubeアカウント
    yt_account = db.query(YouTubeAccount).filter(
        YouTubeAccount.is_active == True
    ).first()

    return {
        "latest_metrics": {
            "week_start_date": latest_metrics.week_start_date.isoformat() if latest_metrics else None,
            "week_end_date": latest_metrics.week_end_date.isoformat() if latest_metrics else None,
            "total_views": latest_metrics.total_views if latest_metrics else 0,
            "total_impressions": latest_metrics.total_impressions if latest_metrics else 0,
            "ctr": latest_metrics.ctr if latest_metrics else 0,
            "avg_view_duration": latest_metrics.avg_view_duration if latest_metrics else 0,
            "avg_view_percentage": latest_metrics.avg_view_percentage if latest_metrics else 0,
            "subscribers_gained": latest_metrics.subscribers_gained if latest_metrics else 0,
            "subscribers_lost": latest_metrics.subscribers_lost if latest_metrics else 0,
            "total_likes": latest_metrics.total_likes if latest_metrics else 0,
            "total_comments": latest_metrics.total_comments if latest_metrics else 0,
            "views_change_rate": latest_metrics.views_change_rate if latest_metrics else 0,
            "ctr_change_rate": latest_metrics.ctr_change_rate if latest_metrics else 0,
        },
        "ai_analysis": {
            "summary": latest_analysis.summary if latest_analysis else None,
            "improvement_points": latest_analysis.improvement_points if latest_analysis else None,
            "next_theme_suggestions": latest_analysis.next_theme_suggestions if latest_analysis else None,
            "analyzed_at": latest_analysis.analyzed_at.isoformat() if latest_analysis and latest_analysis.analyzed_at else None,
        } if latest_analysis else None,
        "active_jobs": [
            {
                "id": str(j.id),
                "status": j.status,
                "progress_percent": j.progress_percent,
                "current_step": j.current_step,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in active_jobs
        ],
        "stats": {
            "waiting_review_count": waiting_review,
            "youtube_connected": yt_account is not None,
            "channel_title": yt_account.channel_title if yt_account else None,
        },
    }
