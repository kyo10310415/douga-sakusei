from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import encrypt_token, decrypt_token
from app.models.user import User
from app.models.youtube import YouTubeAccount, WeeklyMetrics, VideoMetrics
from app.services.youtube_service import youtube_service

router = APIRouter(prefix="/youtube", tags=["YouTube"])


@router.post("/oauth/start")
def start_oauth(current_user: User = Depends(get_current_user)):
    """YouTube OAuth認証を開始"""
    from app.core.config import settings
    if not settings.YOUTUBE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="YouTube OAuth設定がありません")
    url = youtube_service.get_authorization_url()
    return {"authorization_url": url}


@router.get("/oauth/callback")
def oauth_callback(
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """YouTube OAuth コールバック"""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth認証エラー: {error}")

    try:
        tokens = youtube_service.exchange_code_for_tokens(code)
        channel_info = youtube_service.get_channel_info(
            tokens["access_token"], tokens.get("refresh_token", "")
        )

        # 既存チェック
        existing = db.query(YouTubeAccount).filter(
            YouTubeAccount.channel_id == channel_info["channel_id"]
        ).first()

        if existing:
            existing.access_token_encrypted = encrypt_token(tokens["access_token"])
            if tokens.get("refresh_token"):
                existing.refresh_token_encrypted = encrypt_token(tokens["refresh_token"])
            existing.last_synced_at = datetime.utcnow()
            db.commit()
            return {"message": "YouTube連携を更新しました", "channel_id": channel_info["channel_id"]}

        # 最初のユーザーに紐付け（本番では認証済みユーザーに紐付け）
        from app.models.user import User
        first_user = db.query(User).first()

        account = YouTubeAccount(
            user_id=first_user.id if first_user else None,
            channel_id=channel_info["channel_id"],
            channel_title=channel_info.get("title"),
            channel_description=channel_info.get("description"),
            channel_thumbnail_url=channel_info.get("thumbnail_url"),
            subscriber_count=channel_info.get("subscriber_count"),
            video_count=channel_info.get("video_count"),
            view_count=channel_info.get("view_count"),
            access_token_encrypted=encrypt_token(tokens["access_token"]),
            refresh_token_encrypted=encrypt_token(tokens["refresh_token"]) if tokens.get("refresh_token") else None,
            oauth_scopes=tokens.get("scopes", []),
        )
        db.add(account)
        db.commit()

        return {"message": "YouTube連携が完了しました", "channel_id": channel_info["channel_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-weekly")
def sync_weekly_data(
    youtube_account_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """週次データ取得ジョブを手動実行"""
    from app.jobs.youtube_jobs import fetch_weekly_youtube_metrics
    task = fetch_weekly_youtube_metrics.delay(youtube_account_id=youtube_account_id)
    return {"task_id": task.id, "status": "started"}


@router.get("/weekly-metrics")
def get_weekly_metrics(
    limit: int = 12,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """週次メトリクス一覧を取得"""
    metrics = db.query(WeeklyMetrics).order_by(
        WeeklyMetrics.week_start_date.desc()
    ).limit(limit).all()

    result = []
    for m in metrics:
        result.append({
            "id": str(m.id),
            "week_start_date": m.week_start_date.isoformat() if m.week_start_date else None,
            "week_end_date": m.week_end_date.isoformat() if m.week_end_date else None,
            "total_views": m.total_views,
            "total_impressions": m.total_impressions,
            "ctr": m.ctr,
            "avg_view_duration": m.avg_view_duration,
            "avg_view_percentage": m.avg_view_percentage,
            "subscribers_gained": m.subscribers_gained,
            "subscribers_lost": m.subscribers_lost,
            "total_likes": m.total_likes,
            "total_comments": m.total_comments,
            "views_change_rate": m.views_change_rate,
            "ctr_change_rate": m.ctr_change_rate,
        })
    return result


@router.get("/videos")
def get_videos(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """動画一覧を取得"""
    videos = db.query(VideoMetrics).order_by(
        VideoMetrics.published_at.desc()
    ).limit(limit).all()

    return [
        {
            "id": str(v.id),
            "youtube_video_id": v.youtube_video_id,
            "title": v.title,
            "thumbnail_url": v.thumbnail_url,
            "published_at": v.published_at.isoformat() if v.published_at else None,
            "views": v.views,
            "ctr": v.ctr,
            "avg_view_duration": v.avg_view_duration,
            "likes": v.likes,
            "comments": v.comments,
            "views_change_rate": v.views_change_rate,
        }
        for v in videos
    ]


@router.get("/video-metrics/{video_id}")
def get_video_metrics(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """動画別メトリクスを取得"""
    vm = db.query(VideoMetrics).filter(
        VideoMetrics.youtube_video_id == video_id
    ).first()
    if not vm:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    return {
        "id": str(vm.id),
        "youtube_video_id": vm.youtube_video_id,
        "title": vm.title,
        "description": vm.description,
        "published_at": vm.published_at.isoformat() if vm.published_at else None,
        "thumbnail_url": vm.thumbnail_url,
        "duration_seconds": vm.duration_seconds,
        "tags": vm.tags,
        "views": vm.views,
        "impressions": vm.impressions,
        "ctr": vm.ctr,
        "avg_view_duration": vm.avg_view_duration,
        "avg_view_percentage": vm.avg_view_percentage,
        "likes": vm.likes,
        "comments": vm.comments,
        "shares": vm.shares,
        "subscribers_gained": vm.subscribers_gained,
    }
