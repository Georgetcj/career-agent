"""Contracts for user-confirmed, evidence-safe resume tailoring."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SuggestionDecisionRequest(BaseModel):
    decision: Literal["accepted", "rejected"]
    confirmed_text: str | None = Field(default=None, min_length=1, max_length=5_000)


class TailoringSuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    match_gap_id: UUID | None
    suggestion_type: str
    rationale: str
    proposed_text: str
    status: str
    confirmed_text: str | None
    decided_at: datetime | None


class TailoringTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    match_analysis_id: UUID
    source_resume_version_id: UUID
    finalized_resume_version_id: UUID | None
    status: str
    created_at: datetime
    suggestions: list[TailoringSuggestionResponse]


class TailoringFinalizeResponse(BaseModel):
    task: TailoringTaskResponse
    resume_version_id: UUID
