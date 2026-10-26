"""Endpoints for user-supplied job descriptions and explainable resume matching."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from career_agent.api.routers.candidates import get_user_or_404
from career_agent.api.schemas.jobs import (
    JobCreate,
    JobResponse,
    MatchAnalysisResponse,
    MatchRunRequest,
)
from career_agent.infrastructure.database import get_database_session
from career_agent.infrastructure.models import Job, JobDescription, MatchAnalysis
from career_agent.services.job_matching import JobMatchingError, JobMatchingService

router = APIRouter(tags=["jobs"])


def _get_job_for_user_or_404(session: Session, user_id: UUID, job_id: UUID) -> Job:
    job = session.scalar(
        select(Job)
        .options(selectinload(Job.description).selectinload(JobDescription.requirements))
        .where(Job.id == job_id, Job.user_id == user_id)
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job was not found.")
    return job


@router.post(
    "/users/{user_id}/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED
)
def create_job(
    user_id: UUID, payload: JobCreate, session: Session = Depends(get_database_session)
) -> Job:
    """Store a job description manually pasted by its owner."""

    get_user_or_404(session, user_id)
    job = Job(user_id=user_id, **payload.model_dump(mode="json"))
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.post("/users/{user_id}/jobs/{job_id}/parse", response_model=JobResponse)
def parse_job(user_id: UUID, job_id: UUID, session: Session = Depends(get_database_session)) -> Job:
    """Extract deterministic requirements from a stored job description."""

    get_user_or_404(session, user_id)
    job = _get_job_for_user_or_404(session, user_id, job_id)
    JobMatchingService().parse_job(session, job)
    return _get_job_for_user_or_404(session, user_id, job_id)


@router.post(
    "/users/{user_id}/jobs/{job_id}/match",
    response_model=MatchAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def match_job(
    user_id: UUID,
    job_id: UUID,
    payload: MatchRunRequest,
    session: Session = Depends(get_database_session),
) -> MatchAnalysis:
    """Create a traceable first-pass match using only stored resume evidence."""

    get_user_or_404(session, user_id)
    job = _get_job_for_user_or_404(session, user_id, job_id)
    try:
        analysis = JobMatchingService().run_match(session, user_id, job, payload.resume_version_id)
    except JobMatchingError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return _get_analysis_for_user_or_404(session, user_id, analysis.id)


def _get_analysis_for_user_or_404(
    session: Session, user_id: UUID, analysis_id: UUID
) -> MatchAnalysis:
    analysis = session.scalar(
        select(MatchAnalysis)
        .options(selectinload(MatchAnalysis.evidences), selectinload(MatchAnalysis.gaps))
        .where(MatchAnalysis.id == analysis_id, MatchAnalysis.user_id == user_id)
    )
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match analysis was not found."
        )
    return analysis


@router.get("/users/{user_id}/match-analyses/{analysis_id}", response_model=MatchAnalysisResponse)
def get_match_analysis(
    user_id: UUID, analysis_id: UUID, session: Session = Depends(get_database_session)
) -> MatchAnalysis:
    """Load a saved match only when it belongs to the requesting user."""

    get_user_or_404(session, user_id)
    return _get_analysis_for_user_or_404(session, user_id, analysis_id)
