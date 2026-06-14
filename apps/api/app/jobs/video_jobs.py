import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional
from app.jobs.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.video import (
    VideoPlan, Script, ScriptSection, GeneratedVoice,
    GeneratedAsset, RenderJob, GeneratedVideo
)
from app.models.character import CharacterProfile, CharacterImage
from app.models.log import JobLog
from app.services.ai_service import get_ai_service
from app.services.tts_service import get_tts_service
from app.services.render_service import RenderService


@celery_app.task(
    bind=True,
    name="app.jobs.video_jobs.generate_script",
    max_retries=3,
)
def generate_script(self, video_plan_id: str):
    """動画企画から台本を生成"""
    db = SessionLocal()
    render_job = None

    try:
        plan = db.query(VideoPlan).filter(VideoPlan.id == video_plan_id).first()
        if not plan:
            raise Exception(f"動画企画が見つかりません: {video_plan_id}")

        # レンダリングジョブを作成
        render_job = RenderJob(
            video_plan_id=plan.id,
            status="scripting",
            progress_percent=10,
            current_step="台本生成中",
        )
        db.add(render_job)
        db.commit()

        # キャラクター情報取得
        character = None
        if plan.character_id:
            character = db.query(CharacterProfile).filter(
                CharacterProfile.id == plan.character_id
            ).first()

        character_dict = {}
        if character:
            character_dict = {
                "name": character.name,
                "first_person": character.first_person,
                "viewer_address": character.viewer_address,
                "tone": character.tone,
                "personality": character.personality,
                "ng_expressions": character.ng_expressions,
                "speech_samples": character.speech_samples,
            }

        plan_dict = {
            "title": plan.title,
            "goal": plan.goal,
            "target_audience": plan.target_audience,
            "structure": plan.structure,
            "cta": plan.cta,
        }

        ai_service = get_ai_service()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(ai_service.generate_script({
                "character": character_dict,
                "plan": plan_dict,
            }))
        finally:
            loop.close()

        # スクリプト保存
        script = Script(
            video_plan_id=plan.id,
            character_id=plan.character_id,
            hook_text=result.get("hook_text"),
            full_script=result.get("full_script"),
            subtitle_text=result.get("subtitle_text"),
            asset_list=result.get("asset_list"),
            status="completed",
        )
        db.add(script)
        db.flush()

        # セクション保存
        for i, section_data in enumerate(result.get("sections", [])):
            section = ScriptSection(
                script_id=script.id,
                order_index=i,
                section_type=section_data.get("section_type", "main"),
                title=section_data.get("title"),
                duration_seconds=section_data.get("duration_seconds", 60),
                narration=section_data.get("narration"),
                subtitle=section_data.get("subtitle"),
                direction=section_data.get("direction"),
                expression=section_data.get("expression", "normal"),
            )
            db.add(section)

        render_job.status = "generating_voice"
        render_job.progress_percent = 25
        render_job.current_step = "音声生成中"
        db.commit()

        # 次のジョブをキック
        generate_voice.delay(render_job_id=str(render_job.id), script_id=str(script.id))

        return {"status": "success", "script_id": str(script.id)}

    except Exception as exc:
        if render_job:
            render_job.status = "failed"
            render_job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.jobs.video_jobs.generate_voice",
    max_retries=3,
)
def generate_voice(self, render_job_id: str, script_id: str):
    """セクションごとに音声を生成"""
    db = SessionLocal()

    try:
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        script = db.query(Script).filter(Script.id == script_id).first()

        if not script:
            raise Exception(f"スクリプトが見つかりません: {script_id}")

        sections = db.query(ScriptSection).filter(
            ScriptSection.script_id == script.id
        ).order_by(ScriptSection.order_index).all()

        character = None
        if script.character_id:
            character = db.query(CharacterProfile).filter(
                CharacterProfile.id == script.character_id
            ).first()

        tts_service = get_tts_service()
        upload_dir = settings.UPLOAD_DIR
        voice_dir = os.path.join(upload_dir, "voices", str(script_id))
        os.makedirs(voice_dir, exist_ok=True)

        for i, section in enumerate(sections):
            if not section.narration:
                continue

            output_path = os.path.join(voice_dir, f"section_{i:03d}.wav")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(tts_service.generate_voice(
                    text=section.narration,
                    voice_id=character.voice_type if character else None,
                    speech_rate=character.speech_rate if character else 1.0,
                    pitch=character.pitch if character else 0.0,
                    emotion_strength=character.emotion_strength if character else 0.7,
                    output_path=output_path,
                ))
            finally:
                loop.close()

            voice = GeneratedVoice(
                section_id=section.id,
                character_id=script.character_id,
                text=section.narration,
                tts_provider=result.get("provider", "mock"),
                voice_id=character.voice_type if character else None,
                speech_rate=character.speech_rate if character else 1.0,
                pitch=character.pitch if character else 0.0,
                emotion_strength=character.emotion_strength if character else 0.7,
                file_path=output_path if result.get("success") else None,
                file_url=f"{settings.STORAGE_BASE_URL}/voices/{script_id}/section_{i:03d}.wav" if result.get("success") else None,
                duration_seconds=result.get("duration_seconds"),
                status="completed" if result.get("success") else "failed",
                error_message=result.get("error"),
                generated_at=datetime.utcnow(),
            )
            db.add(voice)

        if render_job:
            render_job.status = "generating_assets"
            render_job.progress_percent = 50
            render_job.current_step = "素材生成中"
        db.commit()

        # 次のジョブをキック
        generate_assets.delay(render_job_id=render_job_id, script_id=script_id)

        return {"status": "success", "script_id": script_id}

    except Exception as exc:
        if 'render_job' in locals() and render_job:
            render_job.status = "failed"
            render_job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.jobs.video_jobs.generate_assets",
    max_retries=3,
)
def generate_assets(self, render_job_id: str, script_id: str):
    """背景・挿入素材を生成（MVP: プレースホルダー）"""
    db = SessionLocal()

    try:
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        script = db.query(Script).filter(Script.id == script_id).first()

        if not script:
            raise Exception(f"スクリプトが見つかりません: {script_id}")

        asset_dir = os.path.join(settings.UPLOAD_DIR, "assets", str(script_id))
        os.makedirs(asset_dir, exist_ok=True)

        # デフォルト背景プレースホルダーを生成
        bg_path = os.path.join(asset_dir, "background_default.png")
        if not os.path.exists(bg_path):
            _create_placeholder_image(bg_path, 1920, 1080, "#1a1a2e")

        # セクションごとにデフォルト素材を割り当て
        sections = db.query(ScriptSection).filter(
            ScriptSection.script_id == script.id
        ).all()

        for section in sections:
            asset = GeneratedAsset(
                section_id=section.id,
                render_job_id=render_job.id if render_job else None,
                asset_type="background",
                prompt="テック系グラデーション背景",
                provider="mock",
                file_path=bg_path,
                file_url=f"{settings.STORAGE_BASE_URL}/assets/{script_id}/background_default.png",
                mime_type="image/png",
                width=1920,
                height=1080,
                status="completed",
            )
            db.add(asset)

        if render_job:
            render_job.status = "rendering"
            render_job.progress_percent = 65
            render_job.current_step = "動画レンダリング中"
        db.commit()

        # レンダリングをキック
        render_video.delay(render_job_id=render_job_id, script_id=script_id)

        return {"status": "success"}

    except Exception as exc:
        if 'render_job' in locals() and render_job:
            render_job.status = "failed"
            render_job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.jobs.video_jobs.render_video",
    max_retries=2,
    soft_time_limit=1800,  # 30分
)
def render_video(self, render_job_id: str, script_id: str):
    """FFmpegで動画をレンダリング"""
    db = SessionLocal()

    try:
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        script = db.query(Script).filter(Script.id == script_id).first()
        plan = db.query(VideoPlan).filter(VideoPlan.id == render_job.video_plan_id).first()

        if not render_job or not script:
            raise Exception("レンダリングに必要なデータが見つかりません")

        render_job.started_at = datetime.utcnow()
        db.commit()

        # セクションデータを収集
        sections = db.query(ScriptSection).filter(
            ScriptSection.script_id == script.id
        ).order_by(ScriptSection.order_index).all()

        # キャラクター画像パスを取得
        character_image_path = None
        if plan and plan.character_id:
            char_img = db.query(CharacterImage).filter(
                CharacterImage.character_id == plan.character_id,
                CharacterImage.image_type == "standing",
            ).first()
            if char_img:
                character_image_path = char_img.file_path

        sections_data = []
        for section in sections:
            # 音声ファイルパス取得
            voice = None
            if section.voices:
                voice = section.voices[0] if section.voices else None
            else:
                from app.models.video import GeneratedVoice
                voice = db.query(GeneratedVoice).filter(
                    GeneratedVoice.section_id == section.id,
                    GeneratedVoice.status == "completed",
                ).first()

            # 背景素材パス取得
            bg_asset = db.query(GeneratedAsset).filter(
                GeneratedAsset.section_id == section.id,
                GeneratedAsset.asset_type == "background",
            ).first()

            sections_data.append({
                "title": section.title,
                "narration": section.narration,
                "subtitle": section.subtitle or "",
                "expression": section.expression,
                "duration_seconds": section.duration_seconds or 30,
                "audio_path": voice.file_path if voice else "",
                "character_image_path": character_image_path or "",
                "background_path": bg_asset.file_path if bg_asset else "",
            })

        # 出力ディレクトリ
        output_dir = os.path.join(settings.UPLOAD_DIR, "videos", str(render_job_id))
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "output.mp4")

        render_service = RenderService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                render_service.render_full_video(sections_data, output_path)
            )
        finally:
            loop.close()

        if not result["success"]:
            raise Exception(result.get("error", "レンダリング失敗"))

        # サムネイル生成
        thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")
        loop2 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop2)
        try:
            thumb_result = loop2.run_until_complete(
                render_service.generate_thumbnail(output_path, thumbnail_path)
            )
        finally:
            loop2.close()

        # GeneratedVideoを保存
        generated_video = GeneratedVideo(
            render_job_id=render_job.id,
            video_plan_id=render_job.video_plan_id,
            title=plan.title if plan else "未タイトル",
            description=plan.youtube_description if plan else "",
            tags=plan.youtube_tags if plan else [],
            file_path=output_path,
            file_url=f"{settings.STORAGE_BASE_URL}/videos/{render_job_id}/output.mp4",
            thumbnail_path=thumbnail_path if thumb_result.get("success") else None,
            thumbnail_url=f"{settings.STORAGE_BASE_URL}/videos/{render_job_id}/thumbnail.jpg" if thumb_result.get("success") else None,
            file_size=os.path.getsize(output_path) if os.path.exists(output_path) else 0,
        )
        db.add(generated_video)

        render_job.status = "uploading"
        render_job.progress_percent = 85
        render_job.current_step = "YouTubeアップロード中"
        render_job.output_file_path = output_path
        render_job.output_file_url = generated_video.file_url
        render_job.render_log = result.get("render_log", "")
        render_job.completed_at = datetime.utcnow()
        db.commit()

        # アップロードジョブをキック
        from app.jobs.upload_jobs import upload_to_youtube_unlisted
        upload_to_youtube_unlisted.delay(
            render_job_id=render_job_id,
            generated_video_id=str(generated_video.id),
        )

        return {"status": "success", "generated_video_id": str(generated_video.id)}

    except Exception as exc:
        if 'render_job' in locals() and render_job:
            render_job.status = "failed"
            render_job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


def _create_placeholder_image(path: str, width: int, height: int, color: str):
    """PIL または FFmpeg でプレースホルダー画像を作成"""
    try:
        from PIL import Image, ImageDraw
        # カラーコードをRGBに変換
        color_str = color.lstrip("#")
        r, g, b = int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16)
        img = Image.new("RGB", (width, height), (r, g, b))
        img.save(path)
    except Exception:
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            f"-i", f"color=c={color.lstrip('#')}:size={width}x{height}:duration=1",
            "-frames:v", "1", path
        ], capture_output=True)
