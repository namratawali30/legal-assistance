import asyncio
import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.storage.base import (
    StorageBackend,
    StorageError,
    StorageNotFoundError,
)

logger = logging.getLogger(__name__)


class S3StorageBackend(StorageBackend):
    """
    Production-ready S3-compatible private object storage backend.
    Enforces private bucket access, randomized safe object keys, and server-side encryption.
    """

    def __init__(
        self,
        bucket_name: str | None = None,
        region_name: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        sse: str | None = None,
        s3_client: Any | None = None,
    ):
        self.bucket = bucket_name or settings.object_storage_bucket
        self.region = region_name or settings.object_storage_region
        self.endpoint = endpoint_url or settings.object_storage_endpoint
        self.access_key = access_key_id or settings.object_storage_access_key
        self.secret_key = secret_access_key or settings.object_storage_secret_key
        self.sse = sse if sse is not None else getattr(settings, "object_storage_sse", "AES256")

        if s3_client:
            self._client = s3_client
        else:
            client_kwargs: dict[str, Any] = {
                "service_name": "s3",
                "region_name": self.region,
                "config": Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "standard"},
                ),
            }
            if self.endpoint:
                client_kwargs["endpoint_url"] = self.endpoint
            if self.access_key and self.secret_key:
                client_kwargs["aws_access_key_id"] = self.access_key
                client_kwargs["aws_secret_access_key"] = self.secret_key

            self._client = boto3.client(**client_kwargs)

    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        clean_key = key.lstrip("/")
        loop = asyncio.get_running_loop()

        def _do_put():
            try:
                put_kwargs: dict[str, Any] = {
                    "Bucket": self.bucket,
                    "Key": clean_key,
                    "Body": data,
                    "ContentType": content_type,
                }
                if self.sse and self.sse.strip().lower() not in ("none", "disabled", "false", ""):
                    put_kwargs["ServerSideEncryption"] = self.sse
                self._client.put_object(**put_kwargs)
                return clean_key
            except ClientError as e:
                logger.error(f"S3 put_object failed for key '{clean_key}': {e}")
                raise StorageError(f"Failed to store object in S3: {e}") from e

        return await loop.run_in_executor(None, _do_put)

    async def get(self, key: str) -> bytes:
        clean_key = key.lstrip("/")
        loop = asyncio.get_running_loop()

        def _do_get():
            try:
                resp = self._client.get_object(Bucket=self.bucket, Key=clean_key)
                return resp["Body"].read()
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code in ("NoSuchKey", "404"):
                    raise StorageNotFoundError(f"S3 object '{clean_key}' not found.") from e
                logger.error(f"S3 get_object failed for key '{clean_key}': {e}")
                raise StorageError(f"Failed to retrieve object from S3: {e}") from e

        return await loop.run_in_executor(None, _do_get)

    async def delete(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        loop = asyncio.get_running_loop()

        def _do_delete():
            try:
                self._client.delete_object(Bucket=self.bucket, Key=clean_key)
                return True
            except ClientError as e:
                logger.error(f"S3 delete_object failed for key '{clean_key}': {e}")
                raise StorageError(f"Failed to delete object from S3: {e}") from e

        return await loop.run_in_executor(None, _do_delete)

    async def exists(self, key: str) -> bool:
        clean_key = key.lstrip("/")
        loop = asyncio.get_running_loop()

        def _do_head():
            try:
                self._client.head_object(Bucket=self.bucket, Key=clean_key)
                return True
            except ClientError:
                return False

        return await loop.run_in_executor(None, _do_head)

    async def generate_signed_url(
        self,
        key: str,
        expires_in_seconds: int = 300,
        filename: str | None = None,
    ) -> str | None:
        clean_key = key.lstrip("/")
        loop = asyncio.get_running_loop()

        def _do_presign():
            try:
                params = {
                    "Bucket": self.bucket,
                    "Key": clean_key,
                }
                if filename:
                    safe_filename = filename.replace('"', "").replace("\n", "").replace("\r", "")
                    params["ResponseContentDisposition"] = f'attachment; filename="{safe_filename}"'

                return self._client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params=params,
                    ExpiresIn=expires_in_seconds,
                )
            except ClientError as e:
                logger.error(f"S3 generate_presigned_url failed for key '{clean_key}': {e}")
                return None

        return await loop.run_in_executor(None, _do_presign)
