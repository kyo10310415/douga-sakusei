import asyncio
from datetime import datetime
from typing import Optional
from app.jobs.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.security import decrypt_token
from app.models.video import GeneratedVideo, RenderJob, VideoPlan
from app.models.upload import YouTubeUpload, Approval, ReviewChecklist
from app.models.youtube import YouTubeAccount
from app.models.log import JobLog
from app.services.youtube_service import youtube_service


@celery_app.task(
    bind=True,
    name="app.jobs.upload_jobs.upload_to_youtube_unlisted",
    max_retries=3,
    default_retry_delay=120,
)
def upload_to_youtube_unlisted(self, render_job_id: str, generated_video_id: str):
    """完成動画をYouTubeに限定公開でアップロード"""
    db = SessionLocal()
    yt_upload = None

    try:
        generated_video = db.query(GeneratedVideo).filter(
            GeneratedVideo.id == generated_video_id
        ).first()
        render_job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
        plan = None
        if render_job:
            plan = db.query(VideoPlan).filter(VideoPlan.id == render_job.video_plan_id).first()

        # YouTubeアカウントを取得
        yt_account = db.query(YouTubeAccount).filter(
            YouTubeAccount.is_active == True
        ).first()

        # アップロードレコード作成
        yt_upload = YouTubeUpload(
            generated_video_id=generated_video.id,
            youtube_account_id=yt_account.id if yt_account else None,
            upload_status="uploading",
            title=generated_video.title or (plan.title if plan else "未タイトル"),
            description=generated_video.description or "",
            tags=generated_video.tags or [],
            privacy_status="unlisted",  # 必ず限定公開
        )
        db.add(yt_upload)
        db.commit()

        # YouTubeアカウントがない場合やトークンがない場合はモック
        if not yt_account or not yt_account.access_token_encrypted:
            # モック: 実際のアップロードなし
            yt_upload.upload_status = "unlisted"
            yt_upload.youtube_video_id = f"mock_{generated_video_id[:8]}"
            yt_upload.youtube_url = f"https://www.youtube.com/watch?v=mock_{generated_video_id[:8]}"
            yt_upload.privacy_status = "unlisted"
            yt_upload.uploaded_at = datetime.utcnow()
        else:
            access_token = decrypt_token(yt_account.access_token_encrypted)
            refresh_token = decrypt_token(yt_account.refresh_token_encrypted) if yt_account.refresh_token_encrypted else None

            # タイトルを選択（最初の候補を使用）
            title = yt_upload.title
            if plan and plan.youtube_title_candidates:
                title = plan.youtube_title_candidates[0]

            result = youtube_service.upload_video(
                access_token=access_token,
                refresh_token=refresh_token,
                video_path=generated_video.file_path,
                title=title,
                description=yt_upload.description or "",
                tags=yt_upload.tags or [],
                privacy_status="unlisted",  # 強制的にunlisted
            )

            yt_upload.youtube_video_id = result["youtube_video_id"]
            yt_upload.youtube_url = result["youtube_url"]
            yt_upload.upload_status = "unlisted"
            yt_upload.uploaded_at = datetime.utcnow()

            # サムネイルアップロード
            if generated_video.thumbnail_path:
                try:
                    youtube_service.upload_thumbnail(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        youtube_video_id=result["youtube_video_id"],
                        thumbnail_path=generated_video.thumbnail_path,
                    )
                    yt_upload.thumbnail_uploaded = True
                except Exception:
                    pass

        # レビューチェックリスト作成
        review_checklist = ReviewChecklist(
            generated_video_id=generated_video.id,
        )
        db.add(review_checklist)

        # 承認レコード作成
        approval = Approval(
            youtube_upload_id=yt_upload.id,
            approved_by=None,  # ダミー（後で設定）
            status="pending",
        )
        db.add(approval)

        if render_job:
            render_job.status = "waiting_review"
            render_job.progress_percent = 100
            render_job.current_step = "レビュー待ち"
        db.commit()

        # ジョブログ
        log = JobLog(
            render_job_id=render_job.id if render_job else None,
            job_type="upload_to_youtube_unlisted",
            task_id=self.request.id,
            status="success",
            message=f"YouTube限定公開アップロード完了: {yt_upload.youtube_url}",
            finished_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()

        return {
            "status": "success",
            "youtube_url": yt_upload.youtube_url,
            "youtube_video_id": yt_upload.youtube_video_id,
        }

    except Exception as exc:
        if yt_upload:
            yt_upload.upload_status = "failed"
            yt_upload.error_message = str(exc)
            db.commit()
        if 'render_job' in locals() and render_job:
            render_job.status = "failed"
            render_job.error_message = f"アップロード失敗: {exc}"
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


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
