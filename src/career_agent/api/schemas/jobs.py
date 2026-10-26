"""API contracts for manually supplied job descriptions and resume matching."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    raw_description: str = Field(min_length=20, max_length=50_000)
    company_name: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    source_url: HttpUrl | None = None


class RequirementResponse(BaseModel):
    id: UUID
    category: str
    requirement_text: str
    normalized_key: str | None
    is_required: bool
    ordinal: int

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    id: UUID
    title: str
    company_name: str | None
    city: str | None
    source_url: str | None
    raw_description: str
    parse_status: str
    parse_error: str | None
    parsed_at: datetime | None
    created_at: datetime
    requirements: list[RequirementResponse] = []

    model_config = {"from_attributes": True}


class MatchRunRequest(BaseModel):
    """Optionally pin matching to a particular already-indexed resume version."""

    resume_version_id: UUID | None = None


class MatchEvidenceResponse(BaseModel):
    id: UUID
    jd_requirement_id: UUID | None
    document_chunk_id: UUID | None
    relation_type: str
    evidence_text: str

    model_config = {"from_attributes": True}


class MatchGapResponse(BaseModel):
    id: UUID
    jd_requirement_id: UUID | None
    category: str
    severity: str
    description: str

    model_config = {"from_attributes": True}


class MatchAnalysisResponse(BaseModel):
    id: UUID
    job_id: UUID
    resume_version_id: UUID
    strategy_version: str
    status: str
    overall_score: int
    required_score: int
    bonus_score: int
    evidence_score: int
    summary: str
    created_at: datetime
    evidences: list[MatchEvidenceResponse]
    gaps: list[MatchGapResponse]

    model_config = {"from_attributes": True}
