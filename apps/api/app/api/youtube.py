from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from jose import jwt as pyjwt, JWTError, ExpiredSignatureError

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import encrypt_token, decrypt_token
from app.core.config import settings
from app.models.user import User
from app.models.youtube import YouTubeAccount, WeeklyMetrics, VideoMetrics
from app.services.youtube_service import youtube_service

router = APIRouter(prefix="/youtube", tags=["YouTube"])

# ─────────────────────────────────────────
#  OAuth
# ─────────────────────────────────────────

@router.post("/oauth/start")
def start_oauth(current_user: User = Depends(get_current_user)):
    """YouTube OAuth認証を開始。stateにuser_idを埋め込む"""
    if not settings.YOUTUBE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="YouTube OAuth設定がありません（YOUTUBE_CLIENT_IDを設定してください）")

    # stateトークンにuser_idを埋め込む（署名付き・10分有効）
    state_payload = {"user_id": str(current_user.id), "exp": int(datetime.utcnow().timestamp()) + 600}
    state_token = pyjwt.encode(state_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    url = youtube_service.get_authorization_url(state=state_token)
    return {"authorization_url": url}


@router.get("/oauth/callback")
def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """YouTube OAuthコールバック。stateからuser_idを復元してトークンを保存する"""
    web_url = settings.ALLOWED_ORIGINS.split(",")[0].strip()

    # エラーケース
    if error:
        return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=error&reason={error}")

    if not code:
        return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=error&reason=no_code")

    # stateを検証してユーザーを特定
    user_id: Optional[str] = None
    if state:
        try:
            payload = pyjwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("user_id")
        except ExpiredSignatureError:
            return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=error&reason=state_expired")
        except JWTError:
            return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=error&reason=invalid_state")

    if not user_id:
        return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=error&reason=missing_user")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=error&reason=user_not_found")

    try:
        tokens = youtube_service.exchange_code_for_tokens(code)
    except Exception as e:
        # トークン交換失敗（client_id/secret不正など）
        import logging
        logging.error(f"[YouTube OAuth] token exchange failed: {e}")
        reason = str(e)[:120].replace("\n", " ")
        return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=error&reason=token_exchange_failed")

    # チャンネル情報取得（失敗してもトークン保存は続行）
    channel_info: dict = {}
    channel_id_fallback: Optional[str] = None
    try:
        channel_info = youtube_service.get_channel_info(
            tokens["access_token"], tokens.get("refresh_token", "")
        )
        channel_id_fallback = channel_info.get("channel_id")
    except Exception as e:
        import logging
        logging.warning(f"[YouTube OAuth] get_channel_info failed (YouTube Data API possibly not enabled): {e}")
        # channel_id なしでも一時的に保存できるよう sub から取る
        # access_token の sub クレーム（Google の user_id）を channel_id として使う
        # → 後で sync ジョブで上書き可能
        try:
            import base64, json as _json
            parts = tokens["access_token"].split(".")
            if len(parts) >= 2:
                padded = parts[1] + "=="
                decoded = _json.loads(base64.urlsafe_b64decode(padded))
                channel_id_fallback = decoded.get("sub", f"pending_{user_id[:8]}")
            else:
                channel_id_fallback = f"pending_{user_id[:8]}"
        except Exception:
            channel_id_fallback = f"pending_{user_id[:8]}"

    if not channel_id_fallback:
        channel_id_fallback = f"pending_{user_id[:8]}"

    try:
        # 既存チェック（同チャンネルIDがあれば更新）
        existing = db.query(YouTubeAccount).filter(
            YouTubeAccount.channel_id == channel_id_fallback
        ).first()

        if existing:
            existing.user_id = user.id
            existing.access_token_encrypted = encrypt_token(tokens["access_token"])
            if tokens.get("refresh_token"):
                existing.refresh_token_encrypted = encrypt_token(tokens["refresh_token"])
            if channel_info:
                existing.channel_title = channel_info.get("title")
                existing.channel_thumbnail_url = channel_info.get("thumbnail_url")
                existing.subscriber_count = channel_info.get("subscriber_count")
                existing.video_count = channel_info.get("video_count")
                existing.view_count = channel_info.get("view_count")
            existing.last_synced_at = datetime.utcnow()
            existing.is_active = True
            db.commit()
        else:
            account = YouTubeAccount(
                user_id=user.id,
                channel_id=channel_id_fallback,
                channel_title=channel_info.get("title") if channel_info else None,
                channel_description=channel_info.get("description") if channel_info else None,
                channel_thumbnail_url=channel_info.get("thumbnail_url") if channel_info else None,
                subscriber_count=channel_info.get("subscriber_count") if channel_info else None,
                video_count=channel_info.get("video_count") if channel_info else None,
                view_count=channel_info.get("view_count") if channel_info else None,
                access_token_encrypted=encrypt_token(tokens["access_token"]),
                refresh_token_encrypted=encrypt_token(tokens["refresh_token"]) if tokens.get("refresh_token") else None,
                oauth_scopes=tokens.get("scopes", []),
            )
            db.add(account)
            db.commit()

        # channel_infoが取れなかった場合はwarning付きのsuccessリダイレクト
        if not channel_info:
            return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=success&warning=channel_info_unavailable")

        return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=success")

    except Exception as e:
        import logging
        logging.error(f"[YouTube OAuth] DB save failed: {e}")
        return RedirectResponse(url=f"{web_url}/dashboard/settings?youtube=error&reason=db_save_failed")


# ─────────────────────────────────────────
#  アカウント管理
# ─────────────────────────────────────────

@router.get("/accounts")
def get_youtube_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ログインユーザーの連携済みYouTubeアカウント一覧"""
    accounts = db.query(YouTubeAccount).filter(
        YouTubeAccount.user_id == current_user.id,
        YouTubeAccount.is_active == True,
    ).all()

    return [
        {
            "id": str(a.id),
            "channel_id": a.channel_id,
            "channel_title": a.channel_title,
            "channel_thumbnail_url": a.channel_thumbnail_url,
            "subscriber_count": a.subscriber_count,
            "video_count": a.video_count,
            "view_count": a.view_count,
            "last_synced_at": a.last_synced_at.isoformat() if a.last_synced_at else None,
            "has_refresh_token": bool(a.refresh_token_encrypted),
        }
        for a in accounts
    ]


@router.delete("/accounts/{account_id}")
def disconnect_youtube_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """YouTubeアカウントの連携を切断"""
    account = db.query(YouTubeAccount).filter(
        YouTubeAccount.id == account_id,
        YouTubeAccount.user_id == current_user.id,
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="アカウントが見つかりません")

    account.is_active = False
    account.access_token_encrypted = None
    account.refresh_token_encrypted = None
    db.commit()
    return {"message": "YouTube連携を切断しました"}


# ─────────────────────────────────────────
#  データ取得・メトリクス
# ─────────────────────────────────────────

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
    # ログインユーザーのアカウントに絞る
    account_ids = [
        a.id for a in db.query(YouTubeAccount).filter(
            YouTubeAccount.user_id == current_user.id
        ).all()
    ]

    metrics = db.query(WeeklyMetrics).filter(
        WeeklyMetrics.youtube_account_id.in_(account_ids)
    ).order_by(WeeklyMetrics.week_start_date.desc()).limit(limit).all()

    return [
        {
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
        }
        for m in metrics
    ]


@router.get("/videos")
def get_videos(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """動画一覧を取得"""
    account_ids = [
        a.id for a in db.query(YouTubeAccount).filter(
            YouTubeAccount.user_id == current_user.id
        ).all()
    ]

    videos = db.query(VideoMetrics).filter(
        VideoMetrics.youtube_account_id.in_(account_ids)
    ).order_by(VideoMetrics.published_at.desc()).limit(limit).all()

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
