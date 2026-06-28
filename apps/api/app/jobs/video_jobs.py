"""
Celery バックグラウンドジョブ - 動画生成・アップロードパイプライン
generate_assets → render_video → upload_to_youtube_unlisted
"""
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
from app.services.render_service import RenderService
from app.services.storage_service import storage_service
import logging

logger = logging.getLogger(__name__)


def _run_async(coro):
    """同期コンテキスト（Celeryタスク）から async 関数を呼ぶヘルパー"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ────────────────────────────────────────────────────────────────────
# Step A: 背景素材生成（デフォルトプレースホルダー）
# ────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.jobs.video_jobs.generate_assets",
    max_retries=3,
    queue="video",
)
def generate_assets(self, render_job_id: str, script_id: str):
    """背景素材を生成してDBに登録し、次の render_video タスクをキックする"""
    db = SessionLocal()
    try:
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        script = db.query(Script).filter(Script.id == script_id).first()
        if not script:
            raise Exception(f"スクリプトが見つかりません: {script_id}")

        if render_job:
            render_job.status = "generating_assets"
            render_job.progress_percent = 10
            render_job.current_step = "背景素材を準備中"
            db.commit()

        asset_dir = os.path.join(settings.UPLOAD_DIR, "assets", str(script_id))
        os.makedirs(asset_dir, exist_ok=True)

        # デフォルト背景プレースホルダー
        bg_path = os.path.join(asset_dir, "background_default.png")
        if not os.path.exists(bg_path):
            _create_placeholder_image(bg_path, 1920, 1080, "#1a1a2e")

        sections = db.query(ScriptSection).filter(
            ScriptSection.script_id == script.id
        ).all()

        for section in sections:
            # 既存があればスキップ
            existing = db.query(GeneratedAsset).filter(
                GeneratedAsset.section_id == section.id,
                GeneratedAsset.asset_type == "background",
            ).first()
            if existing:
                continue

            asset = GeneratedAsset(
                section_id=section.id,
                render_job_id=render_job.id if render_job else None,
                asset_type="background",
                prompt="テック系グラデーション背景",
                provider="local",
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
            render_job.progress_percent = 20
            render_job.current_step = "動画レンダリング開始"
        db.commit()

        render_video.apply_async(
            kwargs={"render_job_id": render_job_id, "script_id": script_id},
            queue="video",
        )
        return {"status": "success"}

    except Exception as exc:
        logger.error(f"[generate_assets] error: {exc}")
        if "render_job" in dir() and render_job:
            render_job.status = "failed"
            render_job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────────
# Step B: FFmpeg 動画レンダリング
# ────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.jobs.video_jobs.render_video",
    max_retries=2,
    soft_time_limit=1800,  # 30分
    queue="video",
)
def render_video(self, render_job_id: str, script_id: str):
    """FFmpegでセクション動画を合成し R2 にアップロードする"""
    db = SessionLocal()
    try:
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        script = db.query(Script).filter(Script.id == script_id).first()
        plan = db.query(VideoPlan).filter(
            VideoPlan.id == render_job.video_plan_id
        ).first() if render_job else None

        if not render_job or not script:
            raise Exception("レンダリングに必要なデータが見つかりません")

        render_job.started_at = datetime.utcnow()
        render_job.status = "rendering"
        render_job.progress_percent = 30
        render_job.current_step = "FFmpeg 動画合成中"
        db.commit()

        # キャラクター立ち絵パスを取得
        character_image_path = None
        if plan and plan.character_id:
            char_img = db.query(CharacterImage).filter(
                CharacterImage.character_id == plan.character_id,
                CharacterImage.image_type == "standing",
            ).first()
            if char_img and char_img.file_path and os.path.exists(char_img.file_path):
                character_image_path = char_img.file_path

        # セクションデータ収集
        sections = db.query(ScriptSection).filter(
            ScriptSection.script_id == script.id
        ).order_by(ScriptSection.order_index).all()

        sections_data = []
        for section in sections:
            # 音声ファイルパス（R2 URL or ローカルパス）
            voice = db.query(GeneratedVoice).filter(
                GeneratedVoice.section_id == section.id,
                GeneratedVoice.status == "completed",
            ).first()

            # R2使用時は file_url を一時ダウンロード
            audio_path = ""
            if voice:
                if voice.file_path and os.path.exists(voice.file_path):
                    audio_path = voice.file_path
                elif voice.file_url:
                    # R2 URL から一時ダウンロード
                    audio_path = _download_to_tmp(
                        voice.file_url,
                        f"/tmp/uploads/voices_dl/{render_job_id}/section_{section.order_index:03d}.mp3"
                    )

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
                "audio_path": audio_path,
                "character_image_path": character_image_path or "",
                "background_path": bg_asset.file_path if (bg_asset and bg_asset.file_path) else "",
            })

        # 出力パス
        output_dir = os.path.join(settings.UPLOAD_DIR, "videos", str(render_job_id))
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "output.mp4")

        render_service = RenderService()
        result = _run_async(render_service.render_full_video(sections_data, output_path))

        if not result["success"]:
            raise Exception(result.get("error", "レンダリング失敗"))

        render_job.progress_percent = 70
        render_job.current_step = "R2へ動画アップロード中"
        db.commit()

        # R2 にアップロード
        remote_key = f"videos/{render_job_id}/output.mp4"
        video_url = _run_async(storage_service.upload_file(
            local_path=output_path,
            remote_key=remote_key,
            content_type="video/mp4",
        ))

        # サムネイル生成
        thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")
        thumb_result = _run_async(render_service.generate_thumbnail(output_path, thumbnail_path))
        thumbnail_url = None
        if thumb_result.get("success") and os.path.exists(thumbnail_path):
            thumbnail_url = _run_async(storage_service.upload_file(
                local_path=thumbnail_path,
                remote_key=f"videos/{render_job_id}/thumbnail.jpg",
                content_type="image/jpeg",
            ))

        # GeneratedVideo 保存
        generated_video = GeneratedVideo(
            render_job_id=render_job.id,
            video_plan_id=render_job.video_plan_id,
            title=plan.title if plan else "未タイトル",
            description=plan.youtube_description if plan else "",
            tags=plan.youtube_tags if plan else [],
            file_path=output_path,
            file_url=video_url,
            thumbnail_path=thumbnail_path if thumb_result.get("success") else None,
            thumbnail_url=thumbnail_url,
            file_size=os.path.getsize(output_path) if os.path.exists(output_path) else 0,
        )
        db.add(generated_video)

        render_job.status = "uploading"
        render_job.progress_percent = 80
        render_job.current_step = "YouTube アップロード中"
        render_job.output_file_path = output_path
        render_job.output_file_url = video_url
        render_job.render_log = result.get("render_log", "")
        db.commit()
        db.refresh(generated_video)

        # YouTube アップロードジョブをキック
        from app.jobs.upload_jobs import upload_to_youtube_unlisted
        upload_to_youtube_unlisted.apply_async(
            kwargs={
                "render_job_id": render_job_id,
                "generated_video_id": str(generated_video.id),
            },
            queue="upload",
        )

        return {"status": "success", "generated_video_id": str(generated_video.id)}

    except Exception as exc:
        logger.error(f"[render_video] error: {exc}")
        if "render_job" in dir() and render_job:
            render_job.status = "failed"
            render_job.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────────
# ヘルパー
# ────────────────────────────────────────────────────────────────────

def _download_to_tmp(url: str, local_path: str) -> str:
    """URL からファイルを一時ダウンロードしてパスを返す"""
    import httpx
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        with httpx.Client(timeout=60) as client:
            r = client.get(url)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(r.content)
        return local_path
    except Exception as e:
        logger.warning(f"[render] download failed {url}: {e}")
        return ""


def _create_placeholder_image(path: str, width: int, height: int, color: str):
    """PIL または FFmpeg でプレースホルダー画像を作成"""
    import subprocess
    try:
        from PIL import Image
        color_str = color.lstrip("#")
        r, g, b = int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16)
        img = Image.new("RGB", (width, height), (r, g, b))
        img.save(path)
    except Exception:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={color.lstrip('#')}:size={width}x{height}:duration=1",
            "-frames:v", "1", path
        ], capture_output=True)


# 旧インターフェース互換（celery job の直接呼び出し用）
generate_script = None  # 旧タスク名への参照（削除済み）
