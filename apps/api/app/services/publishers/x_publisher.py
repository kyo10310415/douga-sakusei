"""
X (Twitter) Publisher Adapter — X API Basic プラン対応
tweepy v4 を使用
"""
import logging
from typing import Optional, List

from app.services.publishers.base import PlatformPublisher, PublishResult
from app.core.config import settings

logger = logging.getLogger(__name__)

# tweepy はオプション依存（未インストール時はモックで動作）
try:
    import tweepy  # type: ignore
    _TWEEPY_AVAILABLE = True
except ImportError:
    _TWEEPY_AVAILABLE = False
    logger.warning("tweepy がインストールされていません。X投稿はモード動作します。")


class XPublisher(PlatformPublisher):
    """X (Twitter) への投稿 Adapter"""

    @property
    def platform_name(self) -> str:
        return "x"

    def _get_client(self):
        """Tweepy Client を構築して返す"""
        if not _TWEEPY_AVAILABLE:
            raise RuntimeError("tweepy がインストールされていません。pip install tweepy を実行してください。")

        required = [
            settings.X_API_KEY,
            settings.X_API_SECRET,
            settings.X_ACCESS_TOKEN,
            settings.X_ACCESS_TOKEN_SECRET,
        ]
        if not all(required):
            raise ValueError(
                "X API の認証情報が未設定です。"
                "X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_TOKEN_SECRET を設定してください。"
            )

        return tweepy.Client(
            consumer_key=settings.X_API_KEY,
            consumer_secret=settings.X_API_SECRET,
            access_token=settings.X_ACCESS_TOKEN,
            access_token_secret=settings.X_ACCESS_TOKEN_SECRET,
            bearer_token=settings.X_BEARER_TOKEN or None,
            wait_on_rate_limit=False,
        )

    async def publish(
        self,
        body: str,
        *,
        image_urls: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        cta: Optional[str] = None,
    ) -> PublishResult:
        text = self._build_text(body, hashtags=hashtags, cta=cta)

        # X の文字数制限: Basic は280文字（日本語も1文字カウント）
        if len(text) > 280:
            text = text[:277] + "..."
            logger.warning("X投稿テキストが280文字を超えたため切り詰めました。")

        # ── モック動作（API key 未設定 or tweepy 未インストール） ──
        if not _TWEEPY_AVAILABLE or not settings.X_API_KEY:
            logger.info("[MOCK] X投稿: %s", text[:80])
            return PublishResult(
                success=True,
                platform="x",
                external_post_id="mock_tweet_id_000",
                external_post_url="https://x.com/mock_user/status/mock_tweet_id_000",
                raw_response={"mock": True, "text": text},
            )

        # ── 実際の投稿 ──
        try:
            client = self._get_client()
            response = client.create_tweet(text=text)
            tweet_id = str(response.data["id"])
            tweet_url = f"https://x.com/i/web/status/{tweet_id}"
            logger.info("X投稿成功: tweet_id=%s", tweet_id)
            return PublishResult(
                success=True,
                platform="x",
                external_post_id=tweet_id,
                external_post_url=tweet_url,
                raw_response={"id": tweet_id},
            )
        except Exception as exc:
            logger.error("X投稿失敗: %s", exc)
            return PublishResult(
                success=False,
                platform="x",
                error_message=str(exc),
            )
