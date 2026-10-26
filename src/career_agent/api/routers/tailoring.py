"""User-controlled endpoints for turning verified suggestions into a new resume version."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from career_agent.api.routers.candidates import get_user_or_404
from career_agent.api.schemas.tailoring import (
    SuggestionDecisionRequest,
    TailoringFinalizeResponse,
    TailoringSuggestionResponse,
    TailoringTaskResponse,
)
from career_agent.infrastructure.database import get_database_session
from career_agent.infrastructure.models import ResumeTailoringTask
from career_agent.services.resume_tailoring import ResumeTailoringError, ResumeTailoringService

router = APIRouter(tags=["tailoring"])


def _get_task_or_404(session: Session, user_id: UUID, task_id: UUID) -> ResumeTailoringTask:
    task = session.scalar(
        select(ResumeTailoringTask)
        .options(selectinload(ResumeTailoringTask.suggestions))
        .where(ResumeTailoringTask.id == task_id, ResumeTailoringTask.user_id == user_id)
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tailoring task was not found."
        )
    return task


@router.post(
    "/users/{user_id}/match-analyses/{analysis_id}/tailoring-tasks",
    response_model=TailoringTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tailoring_task(
    user_id: UUID, analysis_id: UUID, session: Session = Depends(get_database_session)
) -> ResumeTailoringTask:
    """Generate reviewable suggestions from one owned match analysis."""

    get_user_or_404(session, user_id)
    try:
        task = ResumeTailoringService().create_task(session, user_id, analysis_id)
    except ResumeTailoringError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return _get_task_or_404(session, user_id, task.id)


@router.get("/users/{user_id}/tailoring-tasks/{task_id}", response_model=TailoringTaskResponse)
def get_tailoring_task(
    user_id: UUID, task_id: UUID, session: Session = Depends(get_database_session)
) -> ResumeTailoringTask:
    """Return one user-owned tailoring task including all review decisions."""

    get_user_or_404(session, user_id)
    return _get_task_or_404(session, user_id, task_id)


@router.patch(
    "/users/{user_id}/tailoring-suggestions/{suggestion_id}",
    response_model=TailoringSuggestionResponse,
)
def decide_tailoring_suggestion(
    user_id: UUID,
    suggestion_id: UUID,
    payload: SuggestionDecisionRequest,
    session: Session = Depends(get_database_session),
):
    """Accept only user-written text or reject a single recommendation."""

    get_user_or_404(session, user_id)
    try:
        return ResumeTailoringService().decide_suggestion(
            session, user_id, suggestion_id, payload.decision, payload.confirmed_text
        )
    except ResumeTailoringError as error:
        if "was not found" in str(error):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error


@router.post(
    "/users/{user_id}/tailoring-tasks/{task_id}/finalize",
    response_model=TailoringFinalizeResponse,
)
def finalize_tailoring_task(
    user_id: UUID, task_id: UUID, session: Session = Depends(get_database_session)
) -> TailoringFinalizeResponse:
    """Create a new text resume version from accepted user-confirmed additions."""

    get_user_or_404(session, user_id)
    try:
        task = ResumeTailoringService().finalize_task(session, user_id, task_id)
    except ResumeTailoringError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    task = _get_task_or_404(session, user_id, task.id)
    if task.finalized_resume_version_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Version missing."
        )
    return TailoringFinalizeResponse(
        task=TailoringTaskResponse.model_validate(task),
        resume_version_id=task.finalized_resume_version_id,
    )
