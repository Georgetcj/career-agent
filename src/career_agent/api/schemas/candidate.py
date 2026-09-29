"""Request and response contracts for candidate and resume metadata."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """A new user identity for the MVP API."""

    email: EmailStr


class UserResponse(BaseModel):
    """Persisted user identity returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    created_at: datetime
    updated_at: datetime


class CandidateProfileUpsert(BaseModel):
    """User-confirmed candidate facts that may be added or replaced."""

    full_name: str | None = Field(default=None, max_length=100)
    target_role: str | None = Field(default=None, max_length=100)
    target_city: str | None = Field(default=None, max_length=100)
    years_of_experience: int | None = Field(default=None, ge=0, le=60)
    education_level: str | None = Field(default=None, max_length=100)


class CandidateProfileResponse(CandidateProfileUpsert):
    """Persisted profile data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class PreferenceUpsert(BaseModel):
    """Explicit job-search preferences, all confirmed by the user."""

    preferred_industries: list[str] = Field(default_factory=list)
    expected_salary_min: int | None = Field(default=None, ge=0)
    expected_salary_max: int | None = Field(default=None, ge=0)
    job_type: str | None = Field(default=None, max_length=50)


class PreferenceResponse(PreferenceUpsert):
    """Persisted preference data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class ResumeCreate(BaseModel):
    """Create a logical resume before uploading a particular file version."""

    title: str = Field(default="默认简历", min_length=1, max_length=200)
    is_primary: bool = False


class ResumeResponse(BaseModel):
    """Persisted logical resume metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class ResumeSourceCreate(BaseModel):
    """Metadata for a future MinIO-uploaded file; this endpoint does not upload files."""

    object_key: str = Field(min_length=1, max_length=500)
    original_filename: str = Field(min_length=1, max_length=255)
    storage_provider: str = Field(default="minio", min_length=1, max_length=50)
    media_type: str | None = Field(default=None, max_length=100)
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)


class ResumeVersionCreate(BaseModel):
    """Create one historical resume version and optional source metadata."""

    content_text: str | None = None
    source_format: Literal["pdf", "docx", "markdown", "latex", "text"]
    source: ResumeSourceCreate | None = None


class ResumeSourceResponse(BaseModel):
    """Persisted object-storage metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_version_id: UUID
    storage_provider: str
    object_key: str
    original_filename: str
    media_type: str | None
    size_bytes: int | None
    sha256: str | None
    created_at: datetime
    updated_at: datetime


class ResumeVersionResponse(BaseModel):
    """Persisted resume version metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_id: UUID
    version_number: int
    content_text: str | None
    source_format: str
    parse_status: str
    index_status: str
    parse_error: str | None
    index_error: str | None
    parser_version: str | None
    indexed_at: datetime | None
    is_current: bool
    created_at: datetime
    updated_at: datetime
    source: ResumeSourceResponse | None


class ResumeUploadResponse(BaseModel):
    """The database records created alongside one MinIO source object."""

    resume: ResumeResponse
    version: ResumeVersionResponse


class ResumeDownloadUrlResponse(BaseModel):
    """A short-lived direct-download URL issued after ownership verification."""

    download_url: str
    expires_in_seconds: int
