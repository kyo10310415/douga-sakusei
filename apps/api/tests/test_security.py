"""
ジョブステータス遷移・セキュリティテスト
"""
import pytest
from sqlalchemy.orm import Session
import uuid


def test_job_status_transitions(client, auth_headers):
    """ジョブステータス遷移のテスト"""
    from app.models.video import RenderJob, VideoPlan
    from app.models.user import User
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()

    # テスト用データ作成
    plan = VideoPlan(
        title="テスト動画",
        status="draft",
    )
    db.add(plan)
    db.flush()

    job = RenderJob(
        video_plan_id=plan.id,
        status="pending",
        progress_percent=0,
    )
    db.add(job)
    db.commit()

    job_id = str(job.id)
    db.close()

    # ジョブ一覧で確認
    res = client.get("/api/video-jobs", headers=auth_headers)
    assert res.status_code == 200


def test_youtube_publish_blocked_without_approval(client, auth_headers):
    """承認なしでYouTube公開が拒否されること（最重要テスト）"""
    from app.models.video import RenderJob, VideoPlan, GeneratedVideo
    from app.models.upload import YouTubeUpload, Approval
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()

    # テスト用動画データ作成
    plan = VideoPlan(title="テスト", status="draft")
    db.add(plan)
    db.flush()

    job = RenderJob(video_plan_id=plan.id, status="waiting_review", progress_percent=100)
    db.add(job)
    db.flush()

    video = GeneratedVideo(
        render_job_id=job.id,
        title="テスト動画",
    )
    db.add(video)
    db.flush()

    # YouTubeアップロードレコード作成（未承認）
    yt_account_id = uuid.uuid4()
    yt_upload = YouTubeUpload(
        generated_video_id=video.id,
        youtube_account_id=yt_account_id,
        upload_status="unlisted",
        privacy_status="unlisted",
        youtube_video_id="test_video_id",
        youtube_url="https://youtube.com/watch?v=test",
    )
    db.add(yt_upload)

    # 承認レコード未作成 or pending
    approval = Approval(
        youtube_upload_id=yt_upload.id,
        approved_by=uuid.uuid4(),
        status="pending",  # 未承認
    )
    db.add(approval)
    db.commit()

    video_id = str(video.id)
    db.close()

    # 公開ボタンを押す（承認なしなので403が返るはず）
    res = client.post(f"/api/reviews/{video_id}/publish", headers=auth_headers)
    assert res.status_code == 403
    assert "承認されていません" in res.json()["detail"]


def test_youtube_publish_allowed_after_approval(client, auth_headers):
    """承認後はYouTube公開が許可されること"""
    from app.models.video import RenderJob, VideoPlan, GeneratedVideo
    from app.models.upload import YouTubeUpload, Approval
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()

    plan = VideoPlan(title="テスト", status="draft")
    db.add(plan)
    db.flush()

    job = RenderJob(video_plan_id=plan.id, status="approved", progress_percent=100)
    db.add(job)
    db.flush()

    video = GeneratedVideo(render_job_id=job.id, title="テスト動画")
    db.add(video)
    db.flush()

    yt_account_id = uuid.uuid4()
    yt_upload = YouTubeUpload(
        generated_video_id=video.id,
        youtube_account_id=yt_account_id,
        upload_status="unlisted",
        privacy_status="unlisted",
        youtube_video_id="test_video_id",
        youtube_url="https://youtube.com/watch?v=test",
    )
    db.add(yt_upload)
    db.flush()

    user_id = uuid.uuid4()
    approval = Approval(
        youtube_upload_id=yt_upload.id,
        approved_by=user_id,
        status="approved",  # 承認済み
    )
    db.add(approval)
    db.commit()

    video_id = str(video.id)
    db.close()

    # 承認済みなのでCeleryタスクが開始されるはず
    # (実際のYouTubeアップロードはモック)
    res = client.post(f"/api/reviews/{video_id}/publish", headers=auth_headers)
    # task_idが返ってくる（200 or 202）
    assert res.status_code == 200
    assert "task_id" in res.json()


def test_failed_job_status(client, auth_headers):
    """失敗したジョブが failed ステータスになること"""
    from app.models.video import RenderJob, VideoPlan
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()

    plan = VideoPlan(title="失敗テスト", status="draft")
    db.add(plan)
    db.flush()

    job = RenderJob(
        video_plan_id=plan.id,
        status="failed",
        error_message="テストエラー",
        progress_percent=30,
        retry_count=0,
        max_retries=3,
    )
    db.add(job)
    db.commit()
    job_id = str(job.id)
    db.close()

    # ジョブ詳細確認
    res = client.get(f"/api/video-jobs/{job_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "テストエラー"

    # 再実行できること
    res2 = client.post(f"/api/video-jobs/{job_id}/retry", headers=auth_headers)
    assert res2.status_code == 200


def test_max_retry_exceeded(client, auth_headers):
    """最大リトライ回数超過でエラー"""
    from app.models.video import RenderJob, VideoPlan
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()

    plan = VideoPlan(title="リトライテスト", status="draft")
    db.add(plan)
    db.flush()

    job = RenderJob(
        video_plan_id=plan.id,
        status="failed",
        retry_count=3,
        max_retries=3,  # 上限に達している
    )
    db.add(job)
    db.commit()
    job_id = str(job.id)
    db.close()

    # 最大リトライ超過でエラー
    res = client.post(f"/api/video-jobs/{job_id}/retry", headers=auth_headers)
    assert res.status_code == 400
    assert "最大リトライ回数" in res.json()["detail"]


def test_cancel_published_job_blocked(client, auth_headers):
    """公開済みジョブはキャンセル不可"""
    from app.models.video import RenderJob, VideoPlan
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()

    plan = VideoPlan(title="公開済みテスト", status="draft")
    db.add(plan)
    db.flush()

    job = RenderJob(
        video_plan_id=plan.id,
        status="published",  # 公開済み
    )
    db.add(job)
    db.commit()
    job_id = str(job.id)
    db.close()

    res = client.post(f"/api/video-jobs/{job_id}/cancel", headers=auth_headers)
    assert res.status_code == 400
