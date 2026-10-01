from abc import ABC, abstractmethod
from typing import Any


class StorageError(Exception):
    """Base exception for storage backend operations."""
    pass


class StorageNotFoundError(StorageError):
    """Raised when an object key is not found in storage."""
    pass


class StorageBackend(ABC):
    """
    Abstract interface for evidence and export file storage backends.
    """

    @abstractmethod
    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Store bytes at key and return key identifier."""
        pass

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve bytes stored at key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete object stored at key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check whether key exists."""
        pass

    @abstractmethod
    async def generate_signed_url(
        self,
        key: str,
        expires_in_seconds: int = 300,
        filename: str | None = None,
    ) -> str | None:
        """Generate short-lived signed download URL if backend supports it."""
        pass
