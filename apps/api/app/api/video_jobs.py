from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import asyncio

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.video import RenderJob, VideoPlan, Script, ScriptSection, GeneratedVoice, GeneratedAsset, GeneratedVideo
from app.models.upload import YouTubeUpload, ReviewChecklist, Approval
from app.models.log import JobLog
from app.models.character import CharacterProfile
from app.models.theme import VideoThemeSetting
from app.services.ai_service import get_ai_service

router = APIRouter(prefix="/video-jobs", tags=["VideoJobs"])


# ─────────────────────────────────────────────
# 同期実行: 企画 → 台本を一気に生成して即返す
# ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    character_id: str
    theme_id: str
    custom_topic: Optional[str] = None  # 任意: テーマに追加指示


@router.post("/generate")
async def generate_script_sync(
    data: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    同期モードで「企画生成 → 台本生成」を実行し結果をその場で返す。
    Celery / Redis 不要。OpenAI キーがあれば GPT-4o を使用、なければ Mock。
    所要時間: Mock ~0.1秒 / GPT-4o ~20-40秒
    """
    # ── キャラクター取得 ──
    character = db.query(CharacterProfile).filter(
        CharacterProfile.id == data.character_id,
        CharacterProfile.user_id == current_user.id,
        CharacterProfile.is_active == True,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")

    # ── テーマ取得 ──
    theme = db.query(VideoThemeSetting).filter(
        VideoThemeSetting.id == data.theme_id,
        VideoThemeSetting.user_id == current_user.id,
        VideoThemeSetting.is_active == True,
    ).first()
    if not theme:
        raise HTTPException(status_code=404, detail="テーマが見つかりません")

    # ── AI サービスを取得（キー有り → OpenAI, なし → Mock）──
    ai_service = get_ai_service()
    is_mock = type(ai_service).__name__ == "MockAIService"

    # ── 入力データ整形 ──
    character_dict = {
        "name": character.name,
        "age_setting": character.age_setting,
        "personality": character.personality,
        "tone": character.tone,
        "first_person": character.first_person,
        "viewer_address": character.viewer_address,
        "speech_samples": character.speech_samples,
        "ng_expressions": character.ng_expressions,
    }

    theme_dict = {
        "main_channel_theme": theme.main_channel_theme,
        "target_audience": theme.target_audience,
        "purposes": theme.purposes,
        "title_policy": theme.title_policy,
        "thumbnail_policy": theme.thumbnail_policy,
        "default_duration_seconds": theme.default_duration_seconds,
    }

    # 任意の追加指示を theme_dict に注入
    if data.custom_topic:
        theme_dict["custom_topic"] = data.custom_topic

    # ── STEP 1: 動画企画生成 ──
    plan_result = await ai_service.generate_video_plan({
        "character": character_dict,
        "theme": theme_dict,
        "analysis": {},
    })

    # ── STEP 2: 台本生成 ──
    script_result = await ai_service.generate_script({
        "character": character_dict,
        "plan": plan_result,
    })

    # ── DB 保存 (VideoPlan + Script + ScriptSection) ──
    video_plan = VideoPlan(
        character_id=character.id,
        theme_id=theme.id,
        title=plan_result.get("title", "未タイトル"),
        goal=plan_result.get("goal"),
        target_audience=plan_result.get("target_audience"),
        total_duration_seconds=plan_result.get("total_duration_seconds", 600),
        structure=plan_result.get("structure"),
        youtube_title_candidates=plan_result.get("youtube_title_candidates"),
        youtube_description=plan_result.get("youtube_description"),
        youtube_tags=plan_result.get("youtube_tags"),
        cta=plan_result.get("cta"),
        status="draft",
    )
    db.add(video_plan)
    db.flush()  # video_plan.id を確定

    script = Script(
        video_plan_id=video_plan.id,
        character_id=character.id,
        hook_text=script_result.get("hook_text"),
        full_script=script_result.get("full_script"),
        subtitle_text=script_result.get("subtitle_text"),
        asset_list=script_result.get("asset_list"),
        status="completed",
    )
    db.add(script)
    db.flush()

    for i, sec in enumerate(script_result.get("sections", [])):
        section = ScriptSection(
            script_id=script.id,
            order_index=i,
            section_type=sec.get("section_type", "main"),
            title=sec.get("title"),
            duration_seconds=sec.get("duration_seconds", 60),
            narration=sec.get("narration"),
            subtitle=sec.get("subtitle"),
            direction=sec.get("direction"),
            expression=sec.get("expression", "normal"),
        )
        db.add(section)

    db.commit()
    db.refresh(video_plan)
    db.refresh(script)

    # ── レスポンス ──
    return {
        "ai_mode": "mock" if is_mock else "openai",
        "video_plan": {
            "id": str(video_plan.id),
            "title": video_plan.title,
            "goal": video_plan.goal,
            "target_audience": video_plan.target_audience,
            "total_duration_seconds": video_plan.total_duration_seconds,
            "structure": video_plan.structure,
            "youtube_title_candidates": video_plan.youtube_title_candidates,
            "youtube_description": video_plan.youtube_description,
            "youtube_tags": video_plan.youtube_tags,
            "cta": video_plan.cta,
        },
        "script": {
            "id": str(script.id),
            "hook_text": script.hook_text,
            "full_script": script.full_script,
            "subtitle_text": script.subtitle_text,
            "asset_list": script.asset_list,
            "sections": [
                {
                    "order_index": s.order_index,
                    "section_type": s.section_type,
                    "title": s.title,
                    "duration_seconds": s.duration_seconds,
                    "narration": s.narration,
                    "subtitle": s.subtitle,
                    "direction": s.direction,
                    "expression": s.expression,
                }
                for s in sorted(script.sections, key=lambda x: x.order_index)
            ],
        },
        "character": {"id": str(character.id), "name": character.name},
        "theme": {"id": str(theme.id), "name": theme.name},
    }


@router.get("/plans")
def list_plans(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """自分が生成した動画企画一覧を返す"""
    plans = (
        db.query(VideoPlan)
        .join(CharacterProfile, VideoPlan.character_id == CharacterProfile.id)
        .filter(CharacterProfile.user_id == current_user.id)
        .order_by(VideoPlan.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "goal": p.goal,
            "total_duration_seconds": p.total_duration_seconds,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "has_script": p.script is not None,
        }
        for p in plans
    ]


@router.get("/plans/{plan_id}")
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """企画 + 台本の詳細を返す"""
    plan = (
        db.query(VideoPlan)
        .join(CharacterProfile, VideoPlan.character_id == CharacterProfile.id)
        .filter(
            VideoPlan.id == plan_id,
            CharacterProfile.user_id == current_user.id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="企画が見つかりません")

    script_data = None
    if plan.script:
        s = plan.script
        script_data = {
            "id": str(s.id),
            "hook_text": s.hook_text,
            "full_script": s.full_script,
            "sections": [
                {
                    "order_index": sec.order_index,
                    "section_type": sec.section_type,
                    "title": sec.title,
                    "duration_seconds": sec.duration_seconds,
                    "narration": sec.narration,
                    "subtitle": sec.subtitle,
                    "direction": sec.direction,
                    "expression": sec.expression,
                }
                for sec in sorted(s.sections, key=lambda x: x.order_index)
            ],
        }

    return {
        "id": str(plan.id),
        "title": plan.title,
        "goal": plan.goal,
        "target_audience": plan.target_audience,
        "total_duration_seconds": plan.total_duration_seconds,
        "structure": plan.structure,
        "youtube_title_candidates": plan.youtube_title_candidates,
        "youtube_description": plan.youtube_description,
        "youtube_tags": plan.youtube_tags,
        "cta": plan.cta,
        "status": plan.status,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "script": script_data,
    }


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
