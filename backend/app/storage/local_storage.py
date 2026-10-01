import os
from pathlib import Path

from app.config import settings
from app.storage.base import (
    StorageBackend,
    StorageError,
    StorageNotFoundError,
)


class LocalStorageBackend(StorageBackend):
    """
    Local filesystem storage backend for development, testing, and E2E runs.
    """

    def __init__(self, root_dir: str | Path | None = None):
        self._custom_root = Path(root_dir).resolve() if root_dir else None

    @property
    def root_path(self) -> Path:
        if self._custom_root:
            return self._custom_root

        upload_dir = Path(settings.upload_dir)
        if upload_dir.is_absolute():
            root = upload_dir.resolve()
        else:
            backend_root = Path(__file__).resolve().parents[2]
            root = (backend_root / upload_dir).resolve()

        os.makedirs(root, exist_ok=True)
        return root

    def _resolve_key(self, key: str) -> Path:
        clean_key = key.lstrip("/\\")
        current_root = self.root_path
        target_path = (current_root / clean_key).resolve(strict=False)
        if not target_path.is_relative_to(current_root):
            raise StorageError("Unsafe storage path traversal detected.")
        return target_path

    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        target_path = self._resolve_key(key)
        os.makedirs(target_path.parent, exist_ok=True)
        temp_path = target_path.with_suffix(f"{target_path.suffix}.tmp")
        try:
            with open(temp_path, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, target_path)
        except Exception as e:
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise StorageError(f"Failed to write file locally: {e}") from e

        return key

    async def get(self, key: str) -> bytes:
        target_path = self._resolve_key(key)
        if not target_path.exists() or not target_path.is_file():
            raise StorageNotFoundError(f"Storage object '{key}' not found.")
        try:
            with open(target_path, "rb") as f:
                return f.read()
        except Exception as e:
            raise StorageError(f"Failed to read local storage file: {e}") from e

    async def delete(self, key: str) -> bool:
        target_path = self._resolve_key(key)
        if not target_path.exists():
            return False
        try:
            os.remove(target_path)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete local storage file: {e}") from e

    async def exists(self, key: str) -> bool:
        target_path = self._resolve_key(key)
        return target_path.exists() and target_path.is_file()

    async def generate_signed_url(
        self,
        key: str,
        expires_in_seconds: int = 300,
        filename: str | None = None,
    ) -> str | None:
        # Local backend does not issue signed URLs; backend handles authenticated streaming.
        return None
