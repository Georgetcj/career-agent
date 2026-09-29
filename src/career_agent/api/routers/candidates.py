"""Minimal user, candidate-profile, and resume metadata endpoints."""

import hashlib
from pathlib import PurePath
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from career_agent.api.schemas.candidate import (
    CandidateProfileResponse,
    CandidateProfileUpsert,
    PreferenceResponse,
    PreferenceUpsert,
    ResumeCreate,
    ResumeDownloadUrlResponse,
    ResumeResponse,
    ResumeUploadResponse,
    ResumeVersionCreate,
    ResumeVersionResponse,
    UserCreate,
    UserResponse,
)
from career_agent.core.config import get_settings
from career_agent.infrastructure.database import get_database_session
from career_agent.infrastructure.models import (
    CandidateProfile,
    Preference,
    Resume,
    ResumeSource,
    ResumeVersion,
    User,
)
from career_agent.infrastructure.object_storage import MinioObjectStorage, ObjectStorageError

router = APIRouter(tags=["candidates"])

ALLOWED_RESUME_TYPES: dict[str, set[str]] = {
    "pdf": {"application/pdf", "application/octet-stream"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}
UPLOAD_CHUNK_SIZE = 1024 * 1024


def get_user_or_404(session: Session, user_id: UUID) -> User:
    """Load a user or expose a consistent HTTP 404 response."""

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found.")
    return user


def get_resume_or_404(session: Session, resume_id: UUID) -> Resume:
    """Load a resume or expose a consistent HTTP 404 response."""

    resume = session.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume was not found.")
    return resume


def get_resume_version_for_user_or_404(
    session: Session, user_id: UUID, resume_version_id: UUID
) -> ResumeVersion:
    """Load a version only when it belongs to the requested user."""

    version = session.scalar(
        select(ResumeVersion)
        .options(selectinload(ResumeVersion.source))
        .join(Resume)
        .where(ResumeVersion.id == resume_version_id, Resume.user_id == user_id)
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume version was not found."
        )
    return version


def validate_and_hash_upload(file: UploadFile, max_size_bytes: int) -> tuple[str, str, int, str]:
    """Validate a PDF/DOCX stream and leave it rewound for the MinIO upload."""

    supplied_name = (file.filename or "").replace("\\", "/")
    original_filename = PurePath(supplied_name).name
    suffix = PurePath(original_filename).suffix.lower().removeprefix(".")
    if suffix not in ALLOWED_RESUME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX resume files are supported.",
        )
    if file.content_type not in ALLOWED_RESUME_TYPES[suffix]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded content type does not match a supported resume format.",
        )

    digest = hashlib.sha256()
    size_bytes = 0
    file.file.seek(0)
    while chunk := file.file.read(UPLOAD_CHUNK_SIZE):
        size_bytes += len(chunk)
        if size_bytes > max_size_bytes:
            file.file.seek(0)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Resume files must not exceed {max_size_bytes} bytes.",
            )
        digest.update(chunk)
    file.file.seek(0)

    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An empty resume file cannot be uploaded.",
        )
    return original_filename, suffix, size_bytes, digest.hexdigest()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, session: Session = Depends(get_database_session)) -> User:
    """Create one user identity, enforcing case-insensitive email uniqueness."""

    user = User(email=str(payload.email).lower())
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered."
        ) from error
    session.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, session: Session = Depends(get_database_session)) -> User:
    """Get an existing user identity."""

    return get_user_or_404(session, user_id)


@router.put("/users/{user_id}/profile", response_model=CandidateProfileResponse)
def upsert_profile(
    user_id: UUID,
    payload: CandidateProfileUpsert,
    session: Session = Depends(get_database_session),
) -> CandidateProfile:
    """Create or replace a user's candidate-profile facts."""

    get_user_or_404(session, user_id)
    profile = session.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    if profile is None:
        profile = CandidateProfile(user_id=user_id, **payload.model_dump())
        session.add(profile)
    else:
        for field_name, value in payload.model_dump().items():
            setattr(profile, field_name, value)

    session.commit()
    session.refresh(profile)
    return profile


@router.get("/users/{user_id}/profile", response_model=CandidateProfileResponse)
def get_profile(
    user_id: UUID, session: Session = Depends(get_database_session)
) -> CandidateProfile:
    """Retrieve candidate-profile facts for one user."""

    get_user_or_404(session, user_id)
    profile = session.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate profile was not found."
        )
    return profile


@router.put("/users/{user_id}/preferences", response_model=PreferenceResponse)
def upsert_preferences(
    user_id: UUID,
    payload: PreferenceUpsert,
    session: Session = Depends(get_database_session),
) -> Preference:
    """Create or replace a user's explicit job-search preferences."""

    get_user_or_404(session, user_id)
    preference = session.scalar(select(Preference).where(Preference.user_id == user_id))
    if preference is None:
        preference = Preference(user_id=user_id, **payload.model_dump())
        session.add(preference)
    else:
        for field_name, value in payload.model_dump().items():
            setattr(preference, field_name, value)

    session.commit()
    session.refresh(preference)
    return preference


@router.get("/users/{user_id}/preferences", response_model=PreferenceResponse)
def get_preferences(user_id: UUID, session: Session = Depends(get_database_session)) -> Preference:
    """Retrieve job-search preferences for one user."""

    get_user_or_404(session, user_id)
    preference = session.scalar(select(Preference).where(Preference.user_id == user_id))
    if preference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences were not found."
        )
    return preference


@router.post(
    "/users/{user_id}/resumes", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED
)
def create_resume(
    user_id: UUID,
    payload: ResumeCreate,
    session: Session = Depends(get_database_session),
) -> Resume:
    """Create a logical resume owned by a user."""

    get_user_or_404(session, user_id)
    if payload.is_primary:
        session.execute(update(Resume).where(Resume.user_id == user_id).values(is_primary=False))

    resume = Resume(user_id=user_id, **payload.model_dump())
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume


@router.get("/users/{user_id}/resumes", response_model=list[ResumeResponse])
def list_resumes(user_id: UUID, session: Session = Depends(get_database_session)) -> list[Resume]:
    """List a user's resume metadata, newest first."""

    get_user_or_404(session, user_id)
    return list(
        session.scalars(
            select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
        )
    )


@router.post(
    "/resumes/{resume_id}/versions",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resume_version(
    resume_id: UUID,
    payload: ResumeVersionCreate,
    session: Session = Depends(get_database_session),
) -> ResumeVersion:
    """Append a version; the latest version is marked as current."""

    get_resume_or_404(session, resume_id)
    version_number = (
        session.scalar(
            select(func.max(ResumeVersion.version_number)).where(
                ResumeVersion.resume_id == resume_id
            )
        )
        or 0
    ) + 1
    session.execute(
        update(ResumeVersion).where(ResumeVersion.resume_id == resume_id).values(is_current=False)
    )

    version = ResumeVersion(
        resume_id=resume_id,
        version_number=version_number,
        content_text=payload.content_text,
        source_format=payload.source_format,
    )
    if payload.source is not None:
        version.source = ResumeSource(**payload.source.model_dump())
    session.add(version)
    session.commit()

    stored_version = session.scalar(
        select(ResumeVersion)
        .options(selectinload(ResumeVersion.source))
        .where(ResumeVersion.id == version.id)
    )
    if stored_version is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume version was not saved.",
        )
    return stored_version


@router.get("/resumes/{resume_id}/versions", response_model=list[ResumeVersionResponse])
def list_resume_versions(
    resume_id: UUID, session: Session = Depends(get_database_session)
) -> list[ResumeVersion]:
    """List a resume's versions with their source metadata."""

    get_resume_or_404(session, resume_id)
    return list(
        session.scalars(
            select(ResumeVersion)
            .options(selectinload(ResumeVersion.source))
            .where(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc())
        )
    )


@router.post(
    "/users/{user_id}/resumes/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_resume(
    user_id: UUID,
    file: UploadFile = File(...),
    title: str = Form("默认简历", min_length=1, max_length=200),
    is_primary: bool = Form(False),
    session: Session = Depends(get_database_session),
) -> ResumeUploadResponse:
    """Upload a source file to MinIO and persist its metadata atomically in PostgreSQL."""

    get_user_or_404(session, user_id)
    settings = get_settings()
    original_filename, source_format, size_bytes, sha256 = validate_and_hash_upload(
        file, settings.resume_upload_max_size_bytes
    )

    resume_id = uuid4()
    version_id = uuid4()
    object_key = f"resumes/{user_id}/{resume_id}/v1/original.{source_format}"
    storage = MinioObjectStorage()

    try:
        storage.put_object(object_key, file.file, size_bytes, file.content_type)
    except ObjectStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Resume storage is unavailable. Please try again later.",
        ) from error

    resume = Resume(id=resume_id, user_id=user_id, title=title, is_primary=is_primary)
    version = ResumeVersion(
        id=version_id,
        resume_id=resume_id,
        version_number=1,
        source_format=source_format,
        parse_status="uploaded",
        is_current=True,
    )
    source = ResumeSource(
        resume_version_id=version_id,
        storage_provider="minio",
        object_key=object_key,
        original_filename=original_filename,
        media_type=file.content_type,
        size_bytes=size_bytes,
        sha256=sha256,
    )
    version.source = source

    try:
        if is_primary:
            session.execute(
                update(Resume).where(Resume.user_id == user_id).values(is_primary=False)
            )
        session.add_all([resume, version])
        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        try:
            storage.remove_object(object_key)
        except ObjectStorageError:
            # A future cleanup job can remove an orphan object after a storage outage.
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume metadata could not be saved.",
        ) from error

    stored_version = session.scalar(
        select(ResumeVersion)
        .options(selectinload(ResumeVersion.source))
        .where(ResumeVersion.id == version_id)
    )
    if stored_version is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume version was not saved.",
        )
    return ResumeUploadResponse(
        resume=ResumeResponse.model_validate(resume),
        version=ResumeVersionResponse.model_validate(stored_version),
    )


@router.get(
    "/users/{user_id}/resume-versions/{resume_version_id}/download-url",
    response_model=ResumeDownloadUrlResponse,
)
def create_resume_download_url(
    user_id: UUID,
    resume_version_id: UUID,
    session: Session = Depends(get_database_session),
) -> ResumeDownloadUrlResponse:
    """Issue a short-lived MinIO URL after verifying resume ownership."""

    get_user_or_404(session, user_id)
    version = get_resume_version_for_user_or_404(session, user_id, resume_version_id)
    if version.source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The resume version does not have an uploaded source file.",
        )

    settings = get_settings()
    try:
        download_url = MinioObjectStorage().create_download_url(
            version.source.object_key, settings.minio_presigned_url_ttl_seconds
        )
    except ObjectStorageError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The stored resume file is unavailable.",
        ) from error
    return ResumeDownloadUrlResponse(
        download_url=download_url,
        expires_in_seconds=settings.minio_presigned_url_ttl_seconds,
    )
