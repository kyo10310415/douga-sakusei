from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.video import GeneratedVideo, RenderJob
from app.models.upload import YouTubeUpload, ReviewChecklist, Approval
from app.models.log import JobLog, ImprovementLog

router = APIRouter(prefix="/reviews", tags=["Reviews"])


class ChecklistUpdate(BaseModel):
    no_factual_errors: Optional[bool] = None
    no_inappropriate_content: Optional[bool] = None
    matches_character: Optional[bool] = None
    video_coherent: Optional[bool] = None
    voice_ok: Optional[bool] = None
    subtitle_ok: Optional[bool] = None
    revision_request: Optional[str] = None
    reviewer_notes: Optional[str] = None


class RegenerateRequest(BaseModel):
    reason: str


@router.get("/{video_id}")
def get_review(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """レビュー情報を取得"""
    video = db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    checklist = db.query(ReviewChecklist).filter(
        ReviewChecklist.generated_video_id == video_id
    ).first()

    yt_upload = db.query(YouTubeUpload).filter(
        YouTubeUpload.generated_video_id == video_id
    ).first()

    approval = None
    if yt_upload:
        approval = db.query(Approval).filter(
            Approval.youtube_upload_id == yt_upload.id
        ).first()

    return {
        "video": {
            "id": str(video.id),
            "title": video.title,
            "description": video.description,
            "tags": video.tags,
            "file_url": video.file_url,
            "thumbnail_url": video.thumbnail_url,
            "duration_seconds": video.duration_seconds,
        },
        "checklist": {
            "id": str(checklist.id) if checklist else None,
            "no_factual_errors": checklist.no_factual_errors if checklist else None,
            "no_inappropriate_content": checklist.no_inappropriate_content if checklist else None,
            "matches_character": checklist.matches_character if checklist else None,
            "video_coherent": checklist.video_coherent if checklist else None,
            "voice_ok": checklist.voice_ok if checklist else None,
            "subtitle_ok": checklist.subtitle_ok if checklist else None,
            "revision_request": checklist.revision_request if checklist else None,
            "reviewer_notes": checklist.reviewer_notes if checklist else None,
            "checked_at": checklist.checked_at.isoformat() if checklist and checklist.checked_at else None,
        } if checklist else None,
        "youtube_upload": {
            "id": str(yt_upload.id) if yt_upload else None,
            "youtube_url": yt_upload.youtube_url if yt_upload else None,
            "youtube_video_id": yt_upload.youtube_video_id if yt_upload else None,
            "privacy_status": yt_upload.privacy_status if yt_upload else None,
            "upload_status": yt_upload.upload_status if yt_upload else None,
        } if yt_upload else None,
        "approval": {
            "id": str(approval.id) if approval else None,
            "status": approval.status if approval else "pending",
            "approved_at": approval.approved_at.isoformat() if approval and approval.approved_at else None,
            "published_at": approval.published_at.isoformat() if approval and approval.published_at else None,
        } if approval else None,
    }


@router.put("/{video_id}/checklist")
def update_checklist(
    video_id: str,
    data: ChecklistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """チェックリストを更新"""
    checklist = db.query(ReviewChecklist).filter(
        ReviewChecklist.generated_video_id == video_id
    ).first()

    if not checklist:
        checklist = ReviewChecklist(generated_video_id=video_id)
        db.add(checklist)

    for key, value in data.dict(exclude_unset=True).items():
        setattr(checklist, key, value)

    checklist.checked_at = datetime.utcnow()
    checklist.checked_by = current_user.id
    db.commit()
    return {"status": "updated"}


@router.post("/{video_id}/request-regenerate")
def request_regenerate(
    video_id: str,
    data: RegenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """再生成依頼"""
    video = db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    # ジョブステータスをリセット
    if video.render_job:
        video.render_job.status = "pending"
        video.render_job.error_message = f"再生成依頼: {data.reason}"

    # チェックリストに修正依頼を記録
    checklist = db.query(ReviewChecklist).filter(
        ReviewChecklist.generated_video_id == video_id
    ).first()
    if checklist:
        checklist.revision_request = data.reason

    log = JobLog(
        job_type="request_regenerate",
        status="success",
        message=f"再生成依頼: {data.reason}",
        user_id=current_user.id,
        action="regenerate",
        resource_type="generated_video",
        resource_id=video_id,
    )
    db.add(log)
    db.commit()
    return {"status": "regenerate_requested"}


@router.post("/{video_id}/approve")
def approve_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """動画を承認（公開ボタンを有効化）"""
    video = db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    yt_upload = db.query(YouTubeUpload).filter(
        YouTubeUpload.generated_video_id == video_id
    ).first()
    if not yt_upload:
        raise HTTPException(status_code=400, detail="YouTubeアップロードが完了していません")

    approval = db.query(Approval).filter(
        Approval.youtube_upload_id == yt_upload.id
    ).first()

    if not approval:
        approval = Approval(
            youtube_upload_id=yt_upload.id,
            approved_by=current_user.id,
        )
        db.add(approval)

    approval.status = "approved"
    approval.approved_at = datetime.utcnow()
    approval.approved_by = current_user.id

    if video.render_job:
        video.render_job.status = "approved"

    log = JobLog(
        job_type="approve",
        status="success",
        message=f"動画を承認しました",
        user_id=current_user.id,
        action="approve",
        resource_type="generated_video",
        resource_id=video_id,
    )
    db.add(log)
    db.commit()
    return {"status": "approved"}


@router.post("/{video_id}/publish")
def publish_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """動画をYouTubeで公開（承認済みのもののみ）"""
    video = db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="動画が見つかりません")

    yt_upload = db.query(YouTubeUpload).filter(
        YouTubeUpload.generated_video_id == video_id
    ).first()
    if not yt_upload:
        raise HTTPException(status_code=400, detail="YouTubeアップロードが完了していません")

    approval = db.query(Approval).filter(
        Approval.youtube_upload_id == yt_upload.id
    ).first()

    if not approval or approval.status != "approved":
        raise HTTPException(
            status_code=403,
            detail="動画が承認されていません。承認してから公開してください。"
        )

    if yt_upload.privacy_status == "public":
        raise HTTPException(status_code=400, detail="既に公開済みです")

    # 公開ジョブを実行
    from app.jobs.upload_jobs import publish_youtube_video
    task = publish_youtube_video.delay(
        youtube_upload_id=str(yt_upload.id),
        approved_by_user_id=str(current_user.id),
    )

    # 操作ログ
    log = JobLog(
        job_type="publish",
        status="started",
        message="YouTube公開処理を開始",
        user_id=current_user.id,
        action="publish",
        resource_type="youtube_upload",
        resource_id=str(yt_upload.id),
    )
    db.add(log)
    db.commit()

    return {"task_id": task.id, "status": "publishing"}
