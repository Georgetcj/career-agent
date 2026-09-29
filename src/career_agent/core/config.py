"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the local API service."""

    database_url: str
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str
    minio_root_password: str
    minio_secure: bool = False
    minio_bucket: str = "career-agent-files"
    minio_presigned_url_ttl_seconds: int = 300
    resume_upload_max_size_bytes: int = 10 * 1024 * 1024
    embedding_provider: str = "openai_compatible"
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 32
    rag_chunk_size_chars: int = 800
    rag_chunk_overlap_chars: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one immutable settings instance for the current process."""

    # BaseSettings populates required fields from the configured environment source.
    return Settings()  # pyright: ignore[reportCallIssue]
