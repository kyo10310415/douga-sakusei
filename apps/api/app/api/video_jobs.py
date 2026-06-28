from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import asyncio
import logging
import os
import traceback

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.video import RenderJob, VideoPlan, Script, ScriptSection, GeneratedVoice, GeneratedAsset, GeneratedVideo
from app.models.upload import YouTubeUpload, ReviewChecklist, Approval
from app.models.log import JobLog
from app.models.character import CharacterProfile
from app.models.theme import VideoThemeSetting
from app.services.ai_service import get_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video-jobs", tags=["VideoJobs"])


# ─────────────────────────────────────────────
# 2ステップ生成: Step1=企画のみ, Step2=台本のみ
# 各ステップを独立したHTTPリクエストに分割して
# Render 30秒タイムアウトを回避する
# ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    character_id: str
    theme_id: str
    custom_topic: Optional[str] = None  # 任意: テーマに追加指示


class GenerateScriptRequest(BaseModel):
    plan_id: str  # Step1で返された plan_id


def _to_str(value) -> str | None:
    """dict/list/その他をTextカラムに安全に格納できる文字列に変換する。
    GPT-4oが型をブレさせて返してくることへの防御。
    - str → そのまま
    - dict/list → json.dumps (UTF-8, ensure_ascii=False)
    - None → None
    - その他 → str()
    """
    import json as _json
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return _json.dumps(value, ensure_ascii=False)
    return str(value)


def _build_character_dict(character: CharacterProfile) -> dict:
    """CharacterProfile → AI入力用 dict"""
    return {
        "name": character.name,
        "age_setting": character.age_setting,
        "personality": character.personality,
        "tone": character.tone,
        "first_person": character.first_person,
        "viewer_address": character.viewer_address,
        "speech_samples": character.speech_samples,
        "ng_expressions": character.ng_expressions,
    }


def _build_theme_dict(theme: VideoThemeSetting, custom_topic: Optional[str] = None) -> dict:
    """VideoThemeSetting → AI入力用 dict"""
    d = {
        "main_channel_theme": theme.main_channel_theme,
        "target_audience": theme.target_audience,
        "purposes": theme.purposes,
        "title_policy": theme.title_policy,
        "thumbnail_policy": theme.thumbnail_policy,
        "default_duration_seconds": theme.default_duration_seconds,
    }
    if custom_topic:
        d["custom_topic"] = custom_topic
    return d


# ── Step 1: 企画のみ生成 (~10-15秒) ──

@router.post("/generate/plan")
async def generate_plan_only(
    data: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    【Step 1/2】 動画企画のみを生成してDBに保存し、plan_idを返す。
    所要時間: Mock ~0.1秒 / GPT-4o ~10-15秒
    次に POST /generate/script を呼び出して台本を生成する。
    """
    try:
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

        ai_service = get_ai_service()
        is_mock = type(ai_service).__name__ == "MockAIService"

        plan_result = await ai_service.generate_video_plan({
            "character": _build_character_dict(character),
            "theme": _build_theme_dict(theme, data.custom_topic),
            "analysis": {},
        })

        # DB保存
        # ── 型安全変換 ──────────────────────────────────────────────
        # GPT-4o はフィールドの型をブレさせて返すことがある
        # Text型カラムには必ず str or None を渡す（dict/list は json.dumps）
        # JSON型カラム (structure/youtube_title_candidates/youtube_tags) は
        # list/dict のまま渡す（既に正しい型ならそのまま、str なら json.loads）
        # ────────────────────────────────────────────────────────────
        import json as _json

        def _as_json(v):
            """JSON型カラム用: str なら loads、list/dict はそのまま"""
            if v is None:
                return None
            if isinstance(v, (list, dict)):
                return v
            if isinstance(v, str):
                try:
                    return _json.loads(v)
                except Exception:
                    return v
            return v

        video_plan = VideoPlan(
            character_id=character.id,
            theme_id=theme.id,
            title=_to_str(plan_result.get("title")) or "未タイトル",
            goal=_to_str(plan_result.get("goal")),
            target_audience=_to_str(plan_result.get("target_audience")),
            total_duration_seconds=plan_result.get("total_duration_seconds", 600),
            structure=_as_json(plan_result.get("structure")),
            youtube_title_candidates=_as_json(plan_result.get("youtube_title_candidates")),
            youtube_description=_to_str(plan_result.get("youtube_description")),
            youtube_tags=_as_json(plan_result.get("youtube_tags")),
            cta=_to_str(plan_result.get("cta")),
            status="draft",
        )
        db.add(video_plan)
        db.commit()
        db.refresh(video_plan)

        return {
            "ai_mode": "mock" if is_mock else "openai",
            "plan_id": str(video_plan.id),
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
            "character": {"id": str(character.id), "name": character.name},
            "theme": {"id": str(theme.id), "name": theme.name},
        }

    except HTTPException:
        raise  # 404などはそのまま再raise

    except Exception as e:
        # 500エラー時にログとレスポンスに詳細を記録
        tb = traceback.format_exc()
        logger.error(f"[generate/plan] 500 error: {e}\n{tb}")
        raise HTTPException(
            status_code=500,
            detail=f"企画生成中にエラーが発生しました: {type(e).__name__}: {str(e)}"
        )


# ── Step 2: 台本のみ生成 (~20-30秒) ──

@router.post("/generate/script")
async def generate_script_from_plan(
    data: GenerateScriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    【Step 2/2】 Step1で生成した plan_id をもとに台本を生成してDBに保存する。
    所要時間: Mock ~0.1秒 / GPT-4o ~20-30秒
    """
    # plan取得（所有権チェック）
    plan = (
        db.query(VideoPlan)
        .join(CharacterProfile, VideoPlan.character_id == CharacterProfile.id)
        .filter(
            VideoPlan.id == data.plan_id,
            CharacterProfile.user_id == current_user.id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="企画が見つかりません")

    # 既に台本がある場合はそれを返す
    if plan.script:
        s = plan.script
        return {
            "ai_mode": "cached",
            "script": {
                "id": str(s.id),
                "hook_text": s.hook_text,
                "full_script": s.full_script,
                "subtitle_text": s.subtitle_text,
                "asset_list": s.asset_list,
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
            },
        }

    character = db.query(CharacterProfile).filter(
        CharacterProfile.id == plan.character_id
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")

    ai_service = get_ai_service()
    is_mock = type(ai_service).__name__ == "MockAIService"

    plan_dict = {
        "title": plan.title,
        "goal": plan.goal,
        "target_audience": plan.target_audience,
        "total_duration_seconds": plan.total_duration_seconds,
        "structure": plan.structure,
        "cta": plan.cta,
    }

    script_result = await ai_service.generate_script({
        "character": _build_character_dict(character),
        "plan": plan_dict,
    })

    # full_script フォールバック
    total_sec = plan.total_duration_seconds or 600
    min_acceptable_chars = int(total_sec * 6.5 * 0.5)
    sections_raw = script_result.get("sections", [])
    generated_full = script_result.get("full_script", "")
    if len(generated_full) < min_acceptable_chars and sections_raw:
        generated_full = "\n\n".join(
            f"【{s.get('title', s.get('section_type', ''))}】\n{s.get('narration', '')}"
            for s in sections_raw
            if s.get("narration")
        )

    # DB保存
    script = Script(
        video_plan_id=plan.id,
        character_id=character.id,
        hook_text=script_result.get("hook_text"),
        full_script=generated_full,
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
    db.refresh(script)

    return {
        "ai_mode": "mock" if is_mock else "openai",
        "script": {
            "id": str(script.id),
            "hook_text": script.hook_text,
            "full_script": script.full_script,
            "subtitle_text": script.subtitle_text,
            "asset_list": script.asset_list,
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
                for sec in sorted(script.sections, key=lambda x: x.order_index)
            ],
        },
    }


# ── Step 3: 音声生成 (~15-60秒、セクション数×TTS時間) ──

class GenerateVoiceRequest(BaseModel):
    script_id: str   # Step2で返された script_id


@router.post("/generate/voice")
async def generate_voice_from_script(
    data: GenerateVoiceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    【Step 3/4】 台本の各セクションを OpenAI TTS で音声生成し R2/ローカルに保存。
    所要時間: セクション数 × 約5-10秒
    """
    try:
        # script 取得（所有権チェック）
        script = (
            db.query(Script)
            .join(VideoPlan, Script.video_plan_id == VideoPlan.id)
            .join(CharacterProfile, VideoPlan.character_id == CharacterProfile.id)
            .filter(
                Script.id == data.script_id,
                CharacterProfile.user_id == current_user.id,
            )
            .first()
        )
        if not script:
            raise HTTPException(status_code=404, detail="台本が見つかりません")

        character = db.query(CharacterProfile).filter(
            CharacterProfile.id == script.character_id
        ).first()

        sections = sorted(script.sections, key=lambda x: x.order_index)

        from app.services.tts_service import get_tts_service
        from app.services.storage_service import storage_service

        tts_service = get_tts_service()
        is_mock = type(tts_service).__name__ == "MockTTSService"

        generated_voices = []
        total_duration = 0.0

        for i, section in enumerate(sections):
            if not section.narration:
                generated_voices.append({
                    "section_id": str(section.id),
                    "order_index": section.order_index,
                    "section_type": section.section_type,
                    "status": "skipped",
                    "file_url": None,
                    "duration_seconds": 0,
                })
                continue

            # 既存の音声があればスキップ
            existing = db.query(GeneratedVoice).filter(
                GeneratedVoice.section_id == section.id,
                GeneratedVoice.status == "completed",
            ).first()
            if existing:
                generated_voices.append({
                    "section_id": str(section.id),
                    "order_index": section.order_index,
                    "section_type": section.section_type,
                    "status": "cached",
                    "file_url": existing.file_url,
                    "duration_seconds": existing.duration_seconds or 0,
                })
                total_duration += existing.duration_seconds or 0
                continue

            # 一時ファイルパス
            remote_key = f"voices/{data.script_id}/section_{i:03d}.mp3"
            tmp_path = storage_service.get_local_tmp_path(remote_key)

            # TTS 生成
            result = await tts_service.generate_voice(
                text=section.narration,
                voice_id=character.voice_type if character else "nova",
                speech_rate=character.speech_rate if character else 1.0,
                pitch=character.pitch if character else 0.0,
                emotion_strength=character.emotion_strength if character else 0.7,
                output_path=tmp_path,
                **({"voice_instructions": character.voice_instructions}
                   if character and character.voice_instructions else {}),
            )

            file_url = None
            if result.get("success") and os.path.exists(tmp_path):
                # R2/S3 にアップロード
                file_url = await storage_service.upload_file(
                    local_path=tmp_path,
                    remote_key=remote_key,
                    content_type="audio/mpeg",
                )
                # R2使用時は一時ファイルを削除
                if settings.STORAGE_PROVIDER != "local":
                    storage_service.delete_local_tmp(tmp_path)

            # DB 保存
            voice = GeneratedVoice(
                section_id=section.id,
                character_id=script.character_id,
                text=section.narration,
                tts_provider=result.get("provider", "mock"),
                voice_id=character.voice_type if character else None,
                speech_rate=character.speech_rate if character else 1.0,
                pitch=character.pitch if character else 0.0,
                emotion_strength=character.emotion_strength if character else 0.7,
                file_path=tmp_path if settings.STORAGE_PROVIDER == "local" else None,
                file_url=file_url,
                duration_seconds=result.get("duration_seconds"),
                status="completed" if result.get("success") else "failed",
                error_message=result.get("error"),
                generated_at=datetime.utcnow(),
            )
            db.add(voice)
            db.flush()

            dur = result.get("duration_seconds") or 0
            total_duration += dur
            generated_voices.append({
                "section_id": str(section.id),
                "order_index": section.order_index,
                "section_type": section.section_type,
                "status": "completed" if result.get("success") else "failed",
                "file_url": file_url,
                "duration_seconds": dur,
                "error": result.get("error"),
            })

        db.commit()

        return {
            "ai_mode": "mock" if is_mock else "openai",
            "script_id": data.script_id,
            "total_duration_seconds": total_duration,
            "voice_count": len([v for v in generated_voices if v["status"] == "completed"]),
            "voices": generated_voices,
        }

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[generate/voice] 500 error: {e}\n{tb}")
        raise HTTPException(
            status_code=500,
            detail=f"音声生成中にエラーが発生しました: {type(e).__name__}: {str(e)}"
        )


# ── Step 4: 動画生成（Celery Background Job として非同期実行）──

class GenerateVideoRequest(BaseModel):
    script_id: str   # Step2で返された script_id


@router.post("/generate/video")
async def generate_video_from_script(
    data: GenerateVideoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    【Step 4/4】 音声＋キャラクター画像を FFmpeg で合成して動画生成し、
    YouTubeに非公開アップロードするジョブを Celery でキックする。
    即時レスポンスで render_job_id を返す（実際の処理はバックグラウンド）。
    進捗は GET /video-jobs/render/{render_job_id} でポーリング。
    """
    try:
        # script 取得（所有権チェック）
        script = (
            db.query(Script)
            .join(VideoPlan, Script.video_plan_id == VideoPlan.id)
            .join(CharacterProfile, VideoPlan.character_id == CharacterProfile.id)
            .filter(
                Script.id == data.script_id,
                CharacterProfile.user_id == current_user.id,
            )
            .first()
        )
        if not script:
            raise HTTPException(status_code=404, detail="台本が見つかりません")

        # 音声が生成済みか確認
        voices = db.query(GeneratedVoice).filter(
            GeneratedVoice.section_id.in_(
                [s.id for s in script.sections]
            ),
            GeneratedVoice.status == "completed",
        ).count()
        if voices == 0:
            raise HTTPException(
                status_code=400,
                detail="音声が未生成です。先に /generate/voice を実行してください。"
            )

        # 既存の RenderJob があれば返す（重複起動防止）
        existing_job = db.query(RenderJob).filter(
            RenderJob.video_plan_id == script.video_plan_id,
            RenderJob.status.notin_(["failed"]),
        ).first()
        if existing_job:
            return {
                "render_job_id": str(existing_job.id),
                "status": existing_job.status,
                "message": "既存のレンダリングジョブが進行中または完了済みです。",
                "progress_percent": existing_job.progress_percent,
            }

        # RenderJob 作成
        render_job = RenderJob(
            video_plan_id=script.video_plan_id,
            status="pending",
            progress_percent=0,
            current_step="動画生成ジョブをキュー投入中",
        )
        db.add(render_job)
        db.commit()
        db.refresh(render_job)

        # Celery ジョブをキック
        from app.jobs.video_jobs import generate_assets
        generate_assets.apply_async(
            kwargs={
                "render_job_id": str(render_job.id),
                "script_id": str(script.id),
            },
            queue="video",
        )

        return {
            "render_job_id": str(render_job.id),
            "status": "pending",
            "message": "動画生成ジョブを開始しました。進捗は /generate/render/{render_job_id} で確認できます。",
            "progress_percent": 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[generate/video] 500 error: {e}\n{tb}")
        raise HTTPException(
            status_code=500,
            detail=f"動画生成ジョブの投入に失敗しました: {type(e).__name__}: {str(e)}"
        )


# ── レンダリング進捗確認 ──

@router.get("/render/{render_job_id}")
def get_render_status(
    render_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    動画レンダリングジョブの進捗を返す。
    フロントエンドが 3秒ごとにポーリングして進捗バーを更新する。
    """
    job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="レンダリングジョブが見つかりません")

    # 完了時は YouTube アップロード情報も返す
    yt_upload_data = None
    if job.status in ("uploading", "waiting_review", "approved", "published"):
        from app.models.upload import YouTubeUpload
        yt = db.query(YouTubeUpload).filter(
            YouTubeUpload.generated_video_id == (
                job.generated_video.id if job.generated_video else None
            )
        ).first()
        if yt:
            yt_upload_data = {
                "youtube_video_id": yt.youtube_video_id,
                "youtube_url": yt.youtube_url,
                "privacy_status": yt.privacy_status,
                "upload_status": yt.upload_status,
            }

    return {
        "render_job_id": render_job_id,
        "status": job.status,
        "progress_percent": job.progress_percent,
        "current_step": job.current_step,
        "error_message": job.error_message,
        "output_file_url": job.output_file_url,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "youtube_upload": yt_upload_data,
    }


# ── 後方互換: 旧エンドポイント（内部で2ステップに委譲） ──


@router.post("/generate")
async def generate_script_sync(
    data: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    【後方互換】企画→台本を一括生成。
    ※ 新しいコードは /generate/plan → /generate/script を使うこと。
    所要時間: Mock ~0.1秒 / GPT-4o ~20-40秒（タイムアウトリスクあり）
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

    # ── full_script フォールバック ──
    # full_script が動画尺の50%未満の文字数なら sections の narration を連結して補完
    # 例: 5分(300秒) → 期待値1950字 → 975字未満なら補完
    total_sec = plan_result.get("total_duration_seconds", 600)
    min_acceptable_chars = int(total_sec * 6.5 * 0.5)  # 期待値の50%
    sections_raw = script_result.get("sections", [])
    generated_full = script_result.get("full_script", "")
    if len(generated_full) < min_acceptable_chars and sections_raw:
        generated_full = "\n\n".join(
            f"【{s.get('title', s.get('section_type', ''))}】\n{s.get('narration', '')}"
            for s in sections_raw
            if s.get("narration")
        )

    # ── DB 保存 (VideoPlan + Script + ScriptSection) ──
    import json as _json

    def _as_json(v):
        if v is None:
            return None
        if isinstance(v, (list, dict)):
            return v
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except Exception:
                return v
        return v

    video_plan = VideoPlan(
        character_id=character.id,
        theme_id=theme.id,
        title=_to_str(plan_result.get("title")) or "未タイトル",
        goal=_to_str(plan_result.get("goal")),
        target_audience=_to_str(plan_result.get("target_audience")),
        total_duration_seconds=plan_result.get("total_duration_seconds", 600),
        structure=_as_json(plan_result.get("structure")),
        youtube_title_candidates=_as_json(plan_result.get("youtube_title_candidates")),
        youtube_description=_to_str(plan_result.get("youtube_description")),
        youtube_tags=_as_json(plan_result.get("youtube_tags")),
        cta=_to_str(plan_result.get("cta")),
        status="draft",
    )
    db.add(video_plan)
    db.flush()  # video_plan.id を確定

    script = Script(
        video_plan_id=video_plan.id,
        character_id=character.id,
        hook_text=script_result.get("hook_text"),
        full_script=generated_full,
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
