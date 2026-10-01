from app.config import settings
from app.storage.base import StorageBackend, StorageError, StorageNotFoundError
from app.storage.local_storage import LocalStorageBackend
from app.storage.s3_storage import S3StorageBackend

_storage_instance: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance

    backend_type = (settings.storage_backend or "local").lower().strip()
    if backend_type == "local":
        _storage_instance = LocalStorageBackend()
    elif backend_type == "s3":
        _storage_instance = S3StorageBackend()
    else:
        raise ValueError(f"Unsupported STORAGE_BACKEND '{backend_type}'. Must be 'local' or 's3'.")

    return _storage_instance


def reset_storage_backend():
    global _storage_instance
    _storage_instance = None
