"""
Platform Publisher 抽象基底クラス
すべての媒体Adapterはこのクラスを継承する
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class PublishResult:
    """投稿結果を統一フォーマットで返す"""
    success: bool
    platform: str
    external_post_id: Optional[str] = None
    external_post_url: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


class PlatformPublisher(ABC):
    """媒体別投稿Adapterの基底クラス"""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """媒体識別子 (x / instagram / tiktok / youtube_shorts)"""
        ...

    @abstractmethod
    async def publish(
        self,
        body: str,
        *,
        image_urls: Optional[List[str]] = None,
        hashtags: Optional[List[str]] = None,
        cta: Optional[str] = None,
    ) -> PublishResult:
        """
        投稿を媒体に送信する

        Args:
            body: 投稿本文
            image_urls: 添付画像URLリスト（対応媒体のみ）
            hashtags: ハッシュタグリスト（本文末尾に自動付加）
            cta: CTAテキスト（本文末尾に追加）

        Returns:
            PublishResult
        """
        ...

    def _build_text(
        self,
        body: str,
        hashtags: Optional[List[str]] = None,
        cta: Optional[str] = None,
    ) -> str:
        """本文 + ハッシュタグ + CTA を結合する"""
        parts = [body.strip()]
        if cta:
            parts.append(f"\n{cta.strip()}")
        if hashtags:
            tag_str = " ".join(
                f"#{t.lstrip('#')}" for t in hashtags
            )
            parts.append(f"\n{tag_str}")
        return "".join(parts)
