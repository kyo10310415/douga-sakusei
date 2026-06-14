"""
APIの基本テスト
"""
import pytest


def test_health_check(client):
    """ヘルスチェックエンドポイント"""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_register_and_login(client):
    """ユーザー登録とログイン"""
    # 登録
    res = client.post("/api/auth/register", json={
        "email": "user@example.com",
        "username": "テストユーザー",
        "password": "password123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["is_admin"] == True  # 最初のユーザーは管理者

    # ログイン
    res2 = client.post("/api/auth/login", json={
        "email": "user@example.com",
        "password": "password123",
    })
    assert res2.status_code == 200
    assert "access_token" in res2.json()


def test_login_wrong_password(client):
    """誤ったパスワードでログイン失敗"""
    client.post("/api/auth/register", json={
        "email": "user2@example.com",
        "username": "ユーザー2",
        "password": "password123",
    })
    res = client.post("/api/auth/login", json={
        "email": "user2@example.com",
        "password": "wrongpassword",
    })
    assert res.status_code == 401


def test_get_me_without_auth(client):
    """認証なしでme取得失敗"""
    res = client.get("/api/auth/me")
    assert res.status_code == 403  # HTTPBearer returns 403 when no token


def test_get_me_with_auth(client, auth_headers):
    """認証ありでme取得成功"""
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "test@example.com"


def test_list_characters_empty(client, auth_headers):
    """キャラクター一覧取得（空）"""
    res = client.get("/api/characters", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_create_character(client, auth_headers):
    """キャラクター作成"""
    res = client.post("/api/characters", json={
        "name": "テストちゃん",
        "age_setting": "17歳",
        "first_person": "わたし",
        "viewer_address": "みんな",
        "tts_provider": "mock",
        "is_default": True,
    }, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "テストちゃん"
    assert data["is_default"] == True


def test_create_theme(client, auth_headers):
    """テーマ設定作成"""
    res = client.post("/api/themes", json={
        "name": "テストテーマ",
        "main_channel_theme": "AI解説チャンネル",
        "target_audience": "IT初心者",
        "is_default": True,
    }, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "テストテーマ"


def test_get_dashboard_summary(client, auth_headers):
    """ダッシュボードサマリー取得"""
    res = client.get("/api/dashboard/summary", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "latest_metrics" in data
    assert "stats" in data


def test_list_weekly_metrics_empty(client, auth_headers):
    """週次メトリクス一覧（空）"""
    res = client.get("/api/youtube/weekly-metrics", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_analysis_reports_empty(client, auth_headers):
    """AI分析レポート一覧（空）"""
    res = client.get("/api/analysis/reports", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_video_jobs_empty(client, auth_headers):
    """ジョブ一覧（空）"""
    res = client.get("/api/video-jobs", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []
