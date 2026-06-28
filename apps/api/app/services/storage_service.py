"""
ストレージサービス - Cloudflare R2（S3互換）/ ローカル対応
音声ファイル・動画ファイルの永続保管に使用
"""
import os
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    STORAGE_PROVIDER 環境変数で切り替え:
      local : /tmp/uploads に保存（開発用・永続化なし）
      r2    : Cloudflare R2（本番・永続化）
      s3    : AWS S3（本番・永続化）
    """

    def __init__(self):
        self.provider = settings.STORAGE_PROVIDER.lower()
        self._client = None

    def _get_client(self):
        """boto3クライアントを遅延初期化（R2/S3共通）"""
        if self._client:
            return self._client
        try:
            import boto3
            from botocore.config import Config

            if self.provider == "r2":
                # Cloudflare R2 は S3 互換 API
                endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
                self._client = boto3.client(
                    "s3",
                    endpoint_url=endpoint_url,
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                    config=Config(signature_version="s3v4"),
                    region_name="auto",
                )
            else:
                # AWS S3
                self._client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.STORAGE_ACCESS_KEY,
                    aws_secret_access_key=settings.STORAGE_SECRET_KEY,
                )
        except Exception as e:
            logger.error(f"[storage] boto3 client init failed: {e}")
            raise
        return self._client

    def _bucket(self) -> str:
        if self.provider == "r2":
            return settings.R2_BUCKET_NAME
        return settings.STORAGE_BUCKET

    def _public_base(self) -> str:
        if self.provider == "r2":
            return settings.R2_PUBLIC_URL.rstrip("/")
        return settings.STORAGE_BASE_URL.rstrip("/")

    # ─────────────────────────────────────────────────────────────────
    # メイン API
    # ─────────────────────────────────────────────────────────────────

    async def upload_file(
        self,
        local_path: str,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        ローカルファイルをストレージにアップロードし、公開URLを返す。
        local_path  : サーバー上のファイルパス
        remote_key  : バケット内のキー（例: voices/script_id/section_000.mp3）
        returns     : 公開URL文字列
        """
        if self.provider == "local":
            # ローカルの場合はそのままURLを返す
            public_url = f"{self._public_base()}/{remote_key}"
            logger.info(f"[storage:local] skip upload → {public_url}")
            return public_url

        try:
            client = self._get_client()
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            client.upload_file(
                local_path,
                self._bucket(),
                remote_key,
                ExtraArgs=extra_args,
            )
            public_url = f"{self._public_base()}/{remote_key}"
            logger.info(f"[storage:{self.provider}] uploaded {remote_key} → {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"[storage:{self.provider}] upload failed: {e}")
            raise

    async def upload_bytes(
        self,
        data: bytes,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        バイト列を直接ストレージにアップロードし、公開URLを返す。
        """
        if self.provider == "local":
            # ローカルの場合は /tmp/uploads に保存
            local_path = os.path.join(settings.UPLOAD_DIR, remote_key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            public_url = f"{self._public_base()}/{remote_key}"
            logger.info(f"[storage:local] saved to {local_path}")
            return public_url

        try:
            import io
            client = self._get_client()
            put_kwargs = {
                "Bucket": self._bucket(),
                "Key": remote_key,
                "Body": io.BytesIO(data),
            }
            if content_type:
                put_kwargs["ContentType"] = content_type

            client.put_object(**put_kwargs)
            public_url = f"{self._public_base()}/{remote_key}"
            logger.info(f"[storage:{self.provider}] uploaded bytes {remote_key} → {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"[storage:{self.provider}] upload_bytes failed: {e}")
            raise

    def get_local_tmp_path(self, remote_key: str) -> str:
        """
        /tmp/uploads 配下の一時ファイルパスを返す（R2アップロード前の作業用）
        ディレクトリは自動作成。
        """
        path = os.path.join(settings.UPLOAD_DIR, remote_key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def delete_local_tmp(self, local_path: str):
        """一時ファイルを削除（R2アップロード後のクリーンアップ用）"""
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"[storage] deleted tmp: {local_path}")
        except Exception as e:
            logger.warning(f"[storage] delete tmp failed: {e}")


# シングルトン
storage_service = StorageService()
