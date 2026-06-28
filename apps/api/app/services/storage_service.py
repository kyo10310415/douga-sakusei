"""
ストレージサービス - Render Disk（ローカルファイルシステム）専用版
APIとCelery Workerが同一コンテナ内で動くため、
/opt/render/project/src/uploads を直接共有できる。
R2/S3 は不要。
"""
import os
import shutil
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Render Disk を使ったローカルストレージ。
    upload_file / upload_bytes は ファイルを UPLOAD_DIR 配下に配置し、
    公開URLを返す（FastAPIの /static マウントで配信）。
    """

    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.base_url = settings.STORAGE_BASE_URL.rstrip("/")

    def _ensure_dir(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    # ─────────────────────────────────────────────────────────────────
    # メイン API（R2版と同じインターフェースを維持）
    # ─────────────────────────────────────────────────────────────────

    async def upload_file(
        self,
        local_path: str,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        ファイルを UPLOAD_DIR/remote_key にコピーし、公開URLを返す。
        local_path == 保存先 の場合はコピー不要（すでに正しい場所にある）。
        """
        dest = os.path.join(self.upload_dir, remote_key)
        self._ensure_dir(dest)

        if os.path.abspath(local_path) != os.path.abspath(dest):
            shutil.copy2(local_path, dest)
            logger.info(f"[storage] copied {local_path} → {dest}")
        else:
            logger.info(f"[storage] already at destination: {dest}")

        public_url = f"{self.base_url}/{remote_key}"
        return public_url

    async def upload_bytes(
        self,
        data: bytes,
        remote_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """バイト列をファイルとして保存し公開URLを返す"""
        dest = os.path.join(self.upload_dir, remote_key)
        self._ensure_dir(dest)

        with open(dest, "wb") as f:
            f.write(data)
        logger.info(f"[storage] wrote bytes → {dest}")

        return f"{self.base_url}/{remote_key}"

    def get_local_tmp_path(self, remote_key: str) -> str:
        """
        TTS生成などで一時的にファイルを書き込むパスを返す。
        Render Disk 上のパスなので、Workerからもそのまま読める。
        """
        path = os.path.join(self.upload_dir, remote_key)
        self._ensure_dir(path)
        return path

    def get_local_path(self, remote_key: str) -> str:
        """公開URLに対応するローカルパスを返す"""
        return os.path.join(self.upload_dir, remote_key)

    def delete_local_tmp(self, local_path: str):
        """不要になった一時ファイルを削除（R2版との互換用）"""
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"[storage] deleted: {local_path}")
        except Exception as e:
            logger.warning(f"[storage] delete failed: {e}")


# シングルトン
storage_service = StorageService()
