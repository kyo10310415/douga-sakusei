"""
Manual Export Publisher
X API 未設定 / 対応していない媒体（Instagram / TikTok / YouTube Shorts）向け
"エクスポート用データ" を返すだけの疑似Adapter
"""
import logging
from typing import Optional, List

from app.services.publishers.base import PlatformPublisher, PublishResult

logger = logging.getLogger(__name__)


class ManualExportPublisher(PlatformPublisher):
    """
    手動投稿用エクスポート Adapter
    実際には外部APIを呼ばず、構造化されたエクスポートデータを返す
    """

    def __init__(self, platform: str):
        self._platform = platform

    @property
    def platform_name(self) -> str:
        return self._platform

    async def publish(
        self,
        body: str,
        *,
        image_urls: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        cta: Optional[str] = None,
    ) -> PublishResult:
        text = self._build_text(body, hashtags=hashtags, cta=cta)
        export_data = {
            "platform": self._platform,
            "text": text,
            "image_urls": image_urls or [],
            "hashtags": hashtags or [],
            "manual_export": True,
            "note": f"{self._platform} は自動投稿に対応していません。テキストをコピーして手動で投稿してください。",
        }
        logger.info("[MANUAL_EXPORT] platform=%s text_length=%d", self._platform, len(text))
        return PublishResult(
            success=True,
            platform=self._platform,
            external_post_id=None,
            external_post_url=None,
            raw_response=export_data,
        )
