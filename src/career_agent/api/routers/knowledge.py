"""Explicit indexing and permission-scoped semantic retrieval endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from career_agent.api.routers.candidates import get_user_or_404
from career_agent.api.schemas.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    ResumeIndexResponse,
)
from career_agent.infrastructure.database import get_database_session
from career_agent.infrastructure.embeddings import EmbeddingError, OpenAICompatibleEmbeddingClient
from career_agent.infrastructure.models import DocumentChunk, ResumeVersion
from career_agent.services.resume_indexing import ResumeIndexingError, ResumeIndexingService

router = APIRouter(tags=["knowledge"])


@router.post(
    "/users/{user_id}/resume-versions/{resume_version_id}/index", response_model=ResumeIndexResponse
)
def index_resume_version(
    user_id: UUID,
    resume_version_id: UUID,
    session: Session = Depends(get_database_session),
) -> ResumeIndexResponse:
    """Parse, chunk, and embed one uploaded resume version on explicit user action."""

    get_user_or_404(session, user_id)
    try:
        version = ResumeIndexingService().index_resume_version(session, user_id, resume_version_id)
    except ResumeIndexingError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume index state could not be saved.",
        ) from error

    chunk_count = session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.resume_version_id == version.id)
    )
    return ResumeIndexResponse(
        resume_version_id=version.id,
        parse_status=version.parse_status,
        index_status=version.index_status,
        chunk_count=chunk_count or 0,
    )


@router.post("/users/{user_id}/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    user_id: UUID,
    payload: KnowledgeSearchRequest,
    session: Session = Depends(get_database_session),
) -> KnowledgeSearchResponse:
    """Return only the requesting user's indexed, current-resume source chunks."""

    get_user_or_404(session, user_id)
    try:
        query_vector = OpenAICompatibleEmbeddingClient().embed([payload.query])[0]
    except EmbeddingError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge search is temporarily unavailable.",
        ) from error

    distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
    rows = session.execute(
        select(DocumentChunk, distance)
        .join(ResumeVersion)
        .where(
            DocumentChunk.user_id == user_id,
            ResumeVersion.is_current.is_(True),
            ResumeVersion.index_status == "indexed",
            DocumentChunk.embedding.is_not(None),
        )
        .order_by(distance)
        .limit(payload.limit)
    ).all()
    return KnowledgeSearchResponse(
        results=[
            KnowledgeSearchResult(
                chunk_id=chunk.id,
                resume_version_id=chunk.resume_version_id,
                chunk_index=chunk.chunk_index,
                section_title=chunk.section_title,
                content=chunk.content,
                distance=float(result_distance),
                embedding_model=chunk.embedding_model,
                created_at=chunk.created_at,
            )
            for chunk, result_distance in rows
        ]
    )
