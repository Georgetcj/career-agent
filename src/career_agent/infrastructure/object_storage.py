"""MinIO-backed object storage for user-owned resume source files."""

from __future__ import annotations

from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from career_agent.core.config import get_settings


class ObjectStorageError(Exception):
    """Raised when a required MinIO object-storage operation fails."""


class MinioObjectStorage:
    """Keep MinIO SDK details outside API routes and database models."""

    def __init__(self) -> None:
        settings = get_settings()
        self.bucket_name = settings.minio_bucket
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )

    def ensure_bucket(self) -> None:
        """Create the configured bucket once when it has not been created yet."""

        try:
            if not self._client.bucket_exists(self.bucket_name):
                self._client.make_bucket(self.bucket_name)
        except (S3Error, OSError) as error:
            raise ObjectStorageError("MinIO bucket is unavailable.") from error

    def put_object(
        self,
        object_key: str,
        data: BinaryIO,
        size_bytes: int,
        media_type: str | None,
    ) -> None:
        """Store one already-validated source file at a unique object key."""

        try:
            self.ensure_bucket()
            self._client.put_object(
                self.bucket_name,
                object_key,
                data,
                length=size_bytes,
                content_type=media_type or "application/octet-stream",
            )
        except (S3Error, OSError) as error:
            raise ObjectStorageError("Could not upload the resume file to MinIO.") from error

    def remove_object(self, object_key: str) -> None:
        """Delete a no-longer-referenced object as a best-effort compensation."""

        try:
            self._client.remove_object(self.bucket_name, object_key)
        except (S3Error, OSError) as error:
            raise ObjectStorageError("Could not delete the MinIO object.") from error

    def get_object_bytes(self, object_key: str) -> bytes:
        """Read one stored object and always release the underlying HTTP connection."""

        response = None
        try:
            response = self._client.get_object(self.bucket_name, object_key)
            return response.read()
        except (S3Error, OSError) as error:
            raise ObjectStorageError("Could not read the MinIO object.") from error
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    def create_download_url(self, object_key: str, expires_in_seconds: int) -> str:
        """Return a temporary direct-download URL only for an existing object."""

        try:
            self._client.stat_object(self.bucket_name, object_key)
            return self._client.presigned_get_object(
                self.bucket_name,
                object_key,
                expires=timedelta(seconds=expires_in_seconds),
            )
        except (S3Error, OSError) as error:
            raise ObjectStorageError("The stored resume file is unavailable.") from error
