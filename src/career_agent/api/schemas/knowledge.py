"""Contracts for explicit resume indexing and grounded knowledge retrieval."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ResumeIndexResponse(BaseModel):
    """Result of parsing and indexing a single resume version."""

    resume_version_id: UUID
    parse_status: str
    index_status: str
    chunk_count: int


class KnowledgeSearchRequest(BaseModel):
    """A user query that is embedded using the configured provider."""

    query: str = Field(min_length=1, max_length=2_000)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    """One retrieved source segment, including enough provenance for later citation."""

    chunk_id: UUID
    resume_version_id: UUID
    chunk_index: int
    section_title: str | None
    content: str
    distance: float
    embedding_model: str | None
    created_at: datetime


class KnowledgeSearchResponse(BaseModel):
    """Ranked semantic search results from the requesting user's current resume versions."""

    results: list[KnowledgeSearchResult]
