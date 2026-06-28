import asyncio
import os
from datetime import datetime
from typing import Optional
from app.jobs.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.security import decrypt_token
from app.models.video import GeneratedVideo, RenderJob, VideoPlan
from app.models.upload import YouTubeUpload, Approval, ReviewChecklist
from app.models.youtube import YouTubeAccount
from app.models.log import JobLog
from app.services.youtube_service import youtube_service
import logging

logger = logging.getLogger(__name__)


def _ensure_local_video(generated_video: GeneratedVideo, render_job_id: str) -> str:
    """
    YouTubeアップロードにはローカルファイルパスが必要。
    R2使用時は file_path が None になるので URL からダウンロードする。
    """
    # ローカルファイルが存在する場合はそのまま
    if generated_video.file_path and os.path.exists(generated_video.file_path):
        return generated_video.file_path

    # R2 URL からダウンロード
    if generated_video.file_url:
        import httpx
        local_path = f"/tmp/uploads/yt_upload/{render_job_id}/output.mp4"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            logger.info(f"[upload] downloading video from R2: {generated_video.file_url}")
            with httpx.Client(timeout=300) as client:
                r = client.get(generated_video.file_url)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(r.content)
            logger.info(f"[upload] downloaded to {local_path}")
            return local_path
        except Exception as e:
            raise Exception(f"R2からの動画ダウンロードに失敗しました: {e}")

    raise Exception("動画ファイルが見つかりません（file_path も file_url も未設定）")


def _ensure_local_thumbnail(generated_video: GeneratedVideo, render_job_id: str) -> Optional[str]:
    """サムネイルも同様にローカル確保"""
    if generated_video.thumbnail_path and os.path.exists(generated_video.thumbnail_path):
        return generated_video.thumbnail_path
    if generated_video.thumbnail_url:
        import httpx
        local_path = f"/tmp/uploads/yt_upload/{render_job_id}/thumbnail.jpg"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            with httpx.Client(timeout=60) as client:
                r = client.get(generated_video.thumbnail_url)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(r.content)
            return local_path
        except Exception:
            return None
    return None


@celery_app.task(
    bind=True,
    name="app.jobs.upload_jobs.upload_to_youtube_unlisted",
    max_retries=3,
    default_retry_delay=120,
    queue="upload",
)
def upload_to_youtube_unlisted(self, render_job_id: str, generated_video_id: str):
    """完成動画をYouTubeに非公開でアップロード"""
    db = SessionLocal()
    yt_upload = None

    try:
        generated_video = db.query(GeneratedVideo).filter(
            GeneratedVideo.id == generated_video_id
        ).first()
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        plan = None
        if render_job:
            plan = db.query(VideoPlan).filter(
                VideoPlan.id == render_job.video_plan_id
            ).first()

        # YouTubeアカウントを取得（動画に紐づくキャラクターのユーザーのもの）
        yt_account = None
        if plan and plan.character_id:
            from app.models.character import CharacterProfile
            char = db.query(CharacterProfile).filter(
                CharacterProfile.id == plan.character_id
            ).first()
            if char:
                yt_account = db.query(YouTubeAccount).filter(
                    YouTubeAccount.user_id == char.user_id,
                    YouTubeAccount.is_active == True,
                ).first()
        # フォールバック: アクティブなアカウントを1件取得
        if not yt_account:
            yt_account = db.query(YouTubeAccount).filter(
                YouTubeAccount.is_active == True
            ).first()

        # タイトルを決定（youtube_title_candidatesの先頭を使用）
        title = generated_video.title or (plan.title if plan else "未タイトル")
        if plan and plan.youtube_title_candidates:
            candidates = plan.youtube_title_candidates
            if isinstance(candidates, list) and candidates:
                title = candidates[0]
            elif isinstance(candidates, str):
                import json as _json
                try:
                    parsed = _json.loads(candidates)
                    if parsed:
                        title = parsed[0]
                except Exception:
                    pass

        # アップロードレコード作成
        yt_upload = YouTubeUpload(
            generated_video_id=generated_video.id,
            youtube_account_id=yt_account.id if yt_account else None,
            upload_status="uploading",
            title=title,
            description=generated_video.description or "",
            tags=generated_video.tags or [],
            privacy_status="private",  # 非公開（unlisted=限定公開 / private=非公開）
        )
        db.add(yt_upload)
        db.commit()

        if not yt_account or not yt_account.access_token_encrypted:
            # YouTubeアカウント未連携 → モック
            logger.warning("[upload] YouTube account not connected → mock upload")
            yt_upload.upload_status = "private"
            yt_upload.youtube_video_id = f"mock_{generated_video_id[:8]}"
            yt_upload.youtube_url = f"https://www.youtube.com/watch?v=mock_{generated_video_id[:8]}"
            yt_upload.privacy_status = "private"
            yt_upload.uploaded_at = datetime.utcnow()
        else:
            access_token = decrypt_token(yt_account.access_token_encrypted)
            refresh_token = (
                decrypt_token(yt_account.refresh_token_encrypted)
                if yt_account.refresh_token_encrypted else None
            )

            # R2対応: ローカルに動画ファイルを確保
            video_path = _ensure_local_video(generated_video, render_job_id)
            thumbnail_path = _ensure_local_thumbnail(generated_video, render_job_id)

            logger.info(f"[upload] uploading to YouTube: {title}")
            result = youtube_service.upload_video(
                access_token=access_token,
                refresh_token=refresh_token,
                video_path=video_path,
                title=title,
                description=yt_upload.description or "",
                tags=yt_upload.tags or [],
                privacy_status="private",  # 非公開でアップロード
            )

            yt_upload.youtube_video_id = result["youtube_video_id"]
            yt_upload.youtube_url = result["youtube_url"]
            yt_upload.upload_status = "private"
            yt_upload.uploaded_at = datetime.utcnow()

            # サムネイルアップロード
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    youtube_service.upload_thumbnail(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        youtube_video_id=result["youtube_video_id"],
                        thumbnail_path=thumbnail_path,
                    )
                    yt_upload.thumbnail_uploaded = True
                    logger.info(f"[upload] thumbnail uploaded")
                except Exception as e:
                    logger.warning(f"[upload] thumbnail upload failed: {e}")

            # 一時ファイルクリーンアップ
            if settings.STORAGE_PROVIDER != "local":
                _cleanup_tmp(video_path)
                if thumbnail_path:
                    _cleanup_tmp(thumbnail_path)

        # レビューチェックリスト作成
        review_checklist = ReviewChecklist(
            generated_video_id=generated_video.id,
        )
        db.add(review_checklist)

        # 承認レコード作成
        approval = Approval(
            youtube_upload_id=yt_upload.id,
            approved_by=None,
            status="pending",
        )
        db.add(approval)

        if render_job:
            render_job.status = "waiting_review"
            render_job.progress_percent = 100
            render_job.current_step = "レビュー待ち"
        db.commit()

        log = JobLog(
            render_job_id=render_job.id if render_job else None,
            job_type="upload_to_youtube_unlisted",
            task_id=self.request.id,
            status="success",
            message=f"YouTube非公開アップロード完了: {yt_upload.youtube_url}",
            finished_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()

        logger.info(f"[upload] done: {yt_upload.youtube_url}")
        return {
            "status": "success",
            "youtube_url": yt_upload.youtube_url,
            "youtube_video_id": yt_upload.youtube_video_id,
        }

    except Exception as exc:
        logger.error(f"[upload] error: {exc}")
        if yt_upload:
            yt_upload.upload_status = "failed"
            yt_upload.error_message = str(exc)
            db.commit()
        if "render_job" in dir() and render_job:
            render_job.status = "failed"
            render_job.error_message = f"アップロード失敗: {exc}"
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


def _cleanup_tmp(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


@celery_app.task(
    bind=True,
    name="app.jobs.upload_jobs.publish_youtube_video",
    max_retries=1,  # 公開は1回のみ（無限リトライ禁止）
)
def publish_youtube_video(
    self,
    youtube_upload_id: str,
    approved_by_user_id: str,
):
    """
    YouTubeに公開する - 必ず人間の承認後にのみ呼び出し可能
    このタスクは直接呼び出し禁止。APIエンドポイント経由でのみ実行。
    """
    db = SessionLocal()

    try:
        yt_upload = db.query(YouTubeUpload).filter(
            YouTubeUpload.id == youtube_upload_id
        ).first()

        if not yt_upload:
            raise Exception(f"YouTubeアップロードが見つかりません: {youtube_upload_id}")

        # 承認チェック（セキュリティ）
        approval = db.query(Approval).filter(
            Approval.youtube_upload_id == yt_upload.id
        ).first()

        if not approval or approval.status != "approved":
            raise Exception("承認されていない動画は公開できません")

        # 現在の状態チェック
        if yt_upload.privacy_status == "public":
            return {"status": "already_public"}

        yt_account = db.query(YouTubeAccount).filter(
            YouTubeAccount.id == yt_upload.youtube_account_id
        ).first()

        if not yt_account or not yt_account.access_token_encrypted:
            # モック: 状態更新のみ
            yt_upload.privacy_status = "public"
            yt_upload.published_at = datetime.utcnow()
        else:
            access_token = decrypt_token(yt_account.access_token_encrypted)
            refresh_token = decrypt_token(yt_account.refresh_token_encrypted) if yt_account.refresh_token_encrypted else None

            result = youtube_service.set_video_public(
                access_token=access_token,
                refresh_token=refresh_token,
                youtube_video_id=yt_upload.youtube_video_id,
            )
            yt_upload.privacy_status = "public"
            yt_upload.published_at = datetime.utcnow()

        # 承認レコード更新
        approval.published_at = datetime.utcnow()
        approval.published_by = approved_by_user_id

        # レンダリングジョブ状態更新
        generated_video = db.query(GeneratedVideo).filter(
            GeneratedVideo.id == yt_upload.generated_video_id
        ).first()
        if generated_video and generated_video.render_job:
            generated_video.render_job.status = "published"

        # 操作ログ
        log = JobLog(
            job_type="publish_youtube_video",
            task_id=self.request.id,
            status="success",
            message=f"YouTube公開完了: {yt_upload.youtube_url}",
            user_id=approved_by_user_id,
            action="publish",
            resource_type="youtube_upload",
            resource_id=youtube_upload_id,
            finished_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()

        return {
            "status": "success",
            "youtube_url": yt_upload.youtube_url,
            "published_at": yt_upload.published_at.isoformat(),
        }

    except Exception as exc:
        log = JobLog(
            job_type="publish_youtube_video",
            task_id=self.request.id,
            status="failed",
            message=str(exc),
            user_id=approved_by_user_id,
            action="publish",
            resource_type="youtube_upload",
            resource_id=youtube_upload_id,
        )
        db.add(log)
        db.commit()
        raise
    finally:
        db.close()
