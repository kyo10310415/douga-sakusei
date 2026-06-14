from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.video import RenderJob, VideoPlan, Script, ScriptSection, GeneratedVoice, GeneratedAsset, GeneratedVideo
from app.models.upload import YouTubeUpload, ReviewChecklist, Approval
from app.models.log import JobLog

router = APIRouter(prefix="/video-jobs", tags=["VideoJobs"])


class VideoJobCreate(BaseModel):
    character_id: Optional[str] = None
    theme_id: Optional[str] = None
    analysis_report_id: Optional[str] = None
    title: Optional[str] = None


@router.get("")
def list_jobs(
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(RenderJob).order_by(RenderJob.created_at.desc())
    if status:
        query = query.filter(RenderJob.status == status)
    jobs = query.limit(limit).all()
    return [_job_to_dict(j) for j in jobs]


@router.post("")
def create_job(
    data: VideoJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """動画生成ジョブを手動開始"""
    from app.jobs.ai_jobs import generate_video_plan

    task = generate_video_plan.delay(analysis_report_id=data.analysis_report_id)
    return {"task_id": task.id, "status": "started"}


@router.get("/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    return _job_to_dict(job, detail=True)


@router.post("/{job_id}/retry")
def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    if job.status not in ["failed"]:
        raise HTTPException(status_code=400, detail="失敗したジョブのみ再実行できます")

    if job.retry_count >= job.max_retries:
        raise HTTPException(status_code=400, detail=f"最大リトライ回数({job.max_retries})に達しています")

    job.retry_count += 1
    job.status = "pending"
    job.error_message = None

    # 台本がある場合は音声生成から再実行
    script = db.query(Script).filter(
        Script.video_plan_id == job.video_plan_id
    ).first()

    if script:
        job.status = "generating_voice"
        from app.jobs.video_jobs import generate_voice
        task = generate_voice.delay(render_job_id=str(job.id), script_id=str(script.id))
    else:
        from app.jobs.ai_jobs import generate_video_plan
        task = generate_video_plan.delay()

    db.commit()
    return {"task_id": task.id, "status": "restarted"}


@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    if job.status in ["published", "approved"]:
        raise HTTPException(status_code=400, detail="承認済みまたは公開済みのジョブはキャンセルできません")

    job.status = "failed"
    job.error_message = "手動キャンセル"

    # ログ
    log = JobLog(
        render_job_id=job.id,
        job_type="cancel",
        status="success",
        message="手動キャンセル",
        user_id=current_user.id,
        action="cancel",
        resource_type="render_job",
        resource_id=job_id,
    )
    db.add(log)
    db.commit()
    return {"status": "cancelled"}


def _job_to_dict(job: RenderJob, detail: bool = False) -> dict:
    result = {
        "id": str(job.id),
        "status": job.status,
        "progress_percent": job.progress_percent,
        "current_step": job.current_step,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "error_message": job.error_message,
        "output_file_url": job.output_file_url,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "celery_task_id": job.celery_task_id,
    }

    if detail:
        # 企画情報
        result["video_plan"] = None
        result["script"] = None
        result["youtube_upload"] = None

    return result
