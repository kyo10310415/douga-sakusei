"""
YouTube API サービス - OAuth認証 + データ取得 + アップロード
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.security import encrypt_token, decrypt_token


class YouTubeService:

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.force-ssl",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]

    def get_authorization_url(self) -> str:
        """OAuth2認証URLを生成"""
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.YOUTUBE_CLIENT_ID,
                    "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                    "redirect_uris": [settings.YOUTUBE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.SCOPES,
        )
        flow.redirect_uri = settings.YOUTUBE_REDIRECT_URI
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return authorization_url

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """認証コードをトークンに交換"""
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.YOUTUBE_CLIENT_ID,
                    "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                    "redirect_uris": [settings.YOUTUBE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.SCOPES,
        )
        flow.redirect_uri = settings.YOUTUBE_REDIRECT_URI
        flow.fetch_token(code=code)
        credentials = flow.credentials

        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            "scopes": list(credentials.scopes) if credentials.scopes else [],
        }

    def _build_credentials(self, access_token: str, refresh_token: str):
        """Google認証情報を構築"""
        from google.oauth2.credentials import Credentials

        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.YOUTUBE_CLIENT_ID,
            client_secret=settings.YOUTUBE_CLIENT_SECRET,
            scopes=self.SCOPES,
        )

    def get_channel_info(self, access_token: str, refresh_token: str) -> Dict[str, Any]:
        """チャンネル基本情報を取得"""
        from googleapiclient.discovery import build

        credentials = self._build_credentials(access_token, refresh_token)
        youtube = build("youtube", "v3", credentials=credentials)

        request = youtube.channels().list(
            part="snippet,statistics",
            mine=True,
        )
        response = request.execute()

        if not response.get("items"):
            raise Exception("チャンネルが見つかりません")

        channel = response["items"][0]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})

        return {
            "channel_id": channel["id"],
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url"),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
        }

    def get_videos_list(
        self,
        access_token: str,
        refresh_token: str,
        max_results: int = 50,
        published_after: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """動画一覧を取得"""
        from googleapiclient.discovery import build

        credentials = self._build_credentials(access_token, refresh_token)
        youtube = build("youtube", "v3", credentials=credentials)

        # チャンネルIDを取得
        channel_info = self.get_channel_info(access_token, refresh_token)
        channel_id = channel_info["channel_id"]

        params = {
            "part": "snippet,contentDetails,statistics",
            "channelId": channel_id,
            "maxResults": max_results,
            "order": "date",
            "type": "video",
        }
        if published_after:
            params["publishedAfter"] = published_after

        request = youtube.search().list(**params)
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            video_id = item["id"].get("videoId")
            if not video_id:
                continue

            snippet = item.get("snippet", {})
            videos.append({
                "youtube_video_id": video_id,
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "published_at": snippet.get("publishedAt"),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "tags": snippet.get("tags", []),
            })

        return videos

    def get_video_analytics(
        self,
        access_token: str,
        refresh_token: str,
        video_id: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """動画別アナリティクスを取得"""
        from googleapiclient.discovery import build

        credentials = self._build_credentials(access_token, refresh_token)
        youtube_analytics = build("youtubeAnalytics", "v2", credentials=credentials)

        response = youtube_analytics.reports().query(
            ids=f"video=={video_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,impressions,impressionClickThroughRate,likes,comments,shares,subscribersGained",
        ).execute()

        rows = response.get("rows", [])
        if not rows:
            return {}

        headers = [h["name"] for h in response.get("columnHeaders", [])]
        row = rows[0]

        result = {}
        for i, header in enumerate(headers):
            result[header] = row[i] if i < len(row) else 0

        return {
            "views": int(result.get("views", 0)),
            "impressions": int(result.get("impressions", 0)),
            "ctr": float(result.get("impressionClickThroughRate", 0)),
            "avg_view_duration": float(result.get("averageViewDuration", 0)),
            "avg_view_percentage": float(result.get("averageViewPercentage", 0)),
            "likes": int(result.get("likes", 0)),
            "comments": int(result.get("comments", 0)),
            "shares": int(result.get("shares", 0)),
            "subscribers_gained": int(result.get("subscribersGained", 0)),
        }

    def upload_video(
        self,
        access_token: str,
        refresh_token: str,
        video_path: str,
        title: str,
        description: str,
        tags: List[str],
        category_id: str = "22",
        privacy_status: str = "unlisted",  # 必ずunlistedで始める
    ) -> Dict[str, Any]:
        """動画をYouTubeにアップロード（必ずunlisted）"""
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        # セキュリティ: privacy_statusを強制的にunlistedに（publicは絶対に許可しない）
        if privacy_status == "public":
            raise ValueError("アップロード時にpublicは設定できません。承認後にpublishAPIを使用してください。")

        credentials = self._build_credentials(access_token, refresh_token)
        youtube = build("youtube", "v3", credentials=credentials)

        body = {
            "snippet": {
                "title": title[:100],  # YouTube制限
                "description": description[:5000],
                "tags": tags[:500],  # YouTube制限
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": "unlisted",  # 強制的にunlisted
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=256 * 1024,
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()

        return {
            "youtube_video_id": response["id"],
            "youtube_url": f"https://www.youtube.com/watch?v={response['id']}",
            "privacy_status": "unlisted",
        }

    def set_video_public(
        self,
        access_token: str,
        refresh_token: str,
        youtube_video_id: str,
    ) -> Dict[str, Any]:
        """動画を公開状態にする（人間の承認後のみ呼び出し可能）"""
        from googleapiclient.discovery import build

        credentials = self._build_credentials(access_token, refresh_token)
        youtube = build("youtube", "v3", credentials=credentials)

        request = youtube.videos().update(
            part="status",
            body={
                "id": youtube_video_id,
                "status": {
                    "privacyStatus": "public",
                },
            },
        )
        response = request.execute()

        return {
            "youtube_video_id": response["id"],
            "privacy_status": response["status"]["privacyStatus"],
        }

    def upload_thumbnail(
        self,
        access_token: str,
        refresh_token: str,
        youtube_video_id: str,
        thumbnail_path: str,
    ) -> bool:
        """サムネイルをアップロード"""
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        credentials = self._build_credentials(access_token, refresh_token)
        youtube = build("youtube", "v3", credentials=credentials)

        request = youtube.thumbnails().set(
            videoId=youtube_video_id,
            media_body=MediaFileUpload(thumbnail_path),
        )
        request.execute()
        return True


youtube_service = YouTubeService()
