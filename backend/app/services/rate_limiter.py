from abc import ABC, abstractmethod
import time
import logging
from collections import defaultdict
import asyncio
from typing import Any

from fastapi import HTTPException, status, Request

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int = 60, detail: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )


class RateLimiterBackend(ABC):
    """Abstract rate limiter backend interface."""

    @abstractmethod
    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        custom_detail: str | None = None,
        force: bool = False,
    ):
        pass


class InMemoryRateLimiterBackend(RateLimiterBackend):
    """
    Sliding window in-memory rate limiter backend.
    Used in development, testing, and single-worker deployments.
    """

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        custom_detail: str | None = None,
        force: bool = False,
    ):
        from app.config import settings

        if settings.environment == "test" and not force:
            return

        now = time.time()
        async with self._lock:
            timestamps = self._requests[key]
            cutoff = now - window_seconds
            valid_timestamps = [t for t in timestamps if t > cutoff]
            self._requests[key] = valid_timestamps

            if len(valid_timestamps) >= max_requests:
                oldest = valid_timestamps[0]
                retry_after = max(1, int(window_seconds - (now - oldest)))
                detail_msg = custom_detail or "Rate limit exceeded. Please try again later."
                raise RateLimitExceeded(retry_after=retry_after, detail=detail_msg)

            valid_timestamps.append(now)

    def reset(self):
        self._requests.clear()


class RedisRateLimiterBackend(RateLimiterBackend):
    """
    Shared Redis rate limiter backend for multi-worker production deployments.
    Uses atomic fixed/sliding window counters and automatic key expiration.
    """

    def __init__(self, redis_client=None, redis_url: str | None = None):
        self._client = redis_client
        self._redis_url = redis_url

    def _get_client(self):
        if self._client is not None:
            return self._client

        from app.config import settings
        url = self._redis_url or getattr(settings, "redis_url", None)
        if not url:
            raise RuntimeError("Redis rate limiter requires REDIS_URL configuration.")

        import redis.asyncio as aioredis
        self._client = aioredis.from_url(url, decode_responses=True)
        return self._client

    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        custom_detail: str | None = None,
        force: bool = False,
    ):
        from app.config import settings

        if settings.environment == "test" and not force:
            return

        try:
            client = self._get_client()
            redis_key = f"ratelimit:{key}"

            pipe = client.pipeline()
            pipe.incr(redis_key)
            pipe.ttl(redis_key)
            results = await pipe.execute()

            current_count = results[0]
            ttl = results[1]

            if current_count == 1 or ttl < 0:
                await client.expire(redis_key, window_seconds)
                ttl = window_seconds

            if current_count > max_requests:
                retry_after = max(1, ttl)
                detail_msg = custom_detail or "Rate limit exceeded. Please try again later."
                raise RateLimitExceeded(retry_after=retry_after, detail=detail_msg)

        except RateLimitExceeded:
            raise
        except Exception as exc:
            logger.error(f"Redis rate limiter failed: {exc}")
            raise RateLimitExceeded(retry_after=60, detail="Rate limiter service error.") from exc

    async def close(self):
        if self._client is not None and hasattr(self._client, "close"):
            await self._client.close()


class RateLimiter:
    """
    Application RateLimiter routing calls to configured RateLimiterBackend.
    """

    def __init__(self, backend: RateLimiterBackend | None = None):
        self._backend = backend

    def _get_backend(self) -> RateLimiterBackend:
        if self._backend:
            return self._backend

        from app.config import settings
        backend_type = (getattr(settings, "rate_limit_backend", "memory") or "memory").lower()
        if backend_type == "redis":
            return RedisRateLimiterBackend()
        return InMemoryRateLimiterBackend()

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int = 10,
        window_seconds: int = 60,
        custom_detail: str | None = None,
        force: bool = False,
    ):
        backend = self._get_backend()
        await backend.check(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
            custom_detail=custom_detail,
            force=force,
        )


rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
