"""Persistence models for a candidate and their resume history."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from career_agent.infrastructure.database import Base


class TimestampedModel:
    """Common creation and update timestamps for persisted entities."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampedModel, Base):
    """The owner of all candidate data in the MVP."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)

    profile: Mapped[CandidateProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    preference: Mapped[Preference | None] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[Resume]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[Job]] = relationship(back_populates="user", cascade="all, delete-orphan")


class CandidateProfile(TimestampedModel, Base):
    """Candidate facts used to personalize job-search guidance."""

    __tablename__ = "candidate_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(100))
    target_role: Mapped[str | None] = mapped_column(String(100))
    target_city: Mapped[str | None] = mapped_column(String(100))
    years_of_experience: Mapped[int | None] = mapped_column(Integer)
    education_level: Mapped[str | None] = mapped_column(String(100))

    user: Mapped[User] = relationship(back_populates="profile")


class Preference(TimestampedModel, Base):
    """A candidate's explicit job-search preferences."""

    __tablename__ = "preferences"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    preferred_industries: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    expected_salary_min: Mapped[int | None] = mapped_column(Integer)
    expected_salary_max: Mapped[int | None] = mapped_column(Integer)
    job_type: Mapped[str | None] = mapped_column(String(50))

    user: Mapped[User] = relationship(back_populates="preference")


class Resume(TimestampedModel, Base):
    """A logical resume with one or more immutable historical versions."""

    __tablename__ = "resumes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="resumes")
    versions: Mapped[list[ResumeVersion]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )


class ResumeVersion(TimestampedModel, Base):
    """One version of a resume, ready for later parsing and RAG indexing."""

    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("resume_id", "version_number", name="uq_resume_versions_resume_version"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    resume_id: Mapped[UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text)
    source_format: Mapped[str] = mapped_column(String(20), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(30), default="uploaded", nullable=False)
    index_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    parse_error: Mapped[str | None] = mapped_column(Text)
    index_error: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str | None] = mapped_column(String(50))
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="versions")
    source: Mapped[ResumeSource | None] = relationship(
        back_populates="resume_version", cascade="all, delete-orphan"
    )
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="resume_version", cascade="all, delete-orphan"
    )


class ResumeSource(TimestampedModel, Base):
    """Metadata that points a resume version to its original object-storage file."""

    __tablename__ = "resume_sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    resume_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    storage_provider: Mapped[str] = mapped_column(String(50), default="minio", nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))

    resume_version: Mapped[ResumeVersion] = relationship(back_populates="source")


class DocumentChunk(TimestampedModel, Base):
    """A traceable, embedded segment of one parsed resume version."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "resume_version_id", "chunk_index", name="uq_document_chunks_version_index"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer)

    resume_version: Mapped[ResumeVersion] = relationship(back_populates="chunks")


class Job(TimestampedModel, Base):
    """A job posting pasted by one user; no third-party job-board scraping is implied."""

    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    parse_error: Mapped[str | None] = mapped_column(Text)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="jobs")
    description: Mapped[JobDescription | None] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )
    analyses: Mapped[list[MatchAnalysis]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    @property
    def requirements(self) -> list[JDRequirement]:
        """Expose parsed requirements at the API boundary without duplicating their ownership."""

        return self.description.requirements if self.description is not None else []


class JobDescription(TimestampedModel, Base):
    """A parsed, versioned representation of a single pasted job description."""

    __tablename__ = "job_descriptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    job: Mapped[Job] = relationship(back_populates="description")
    requirements: Mapped[list[JDRequirement]] = relationship(
        back_populates="job_description", cascade="all, delete-orphan"
    )


class JDRequirement(TimestampedModel, Base):
    """One requirement extracted deterministically from a job description."""

    __tablename__ = "jd_requirements"
    __table_args__ = (
        UniqueConstraint(
            "job_description_id", "ordinal", name="uq_jd_requirements_description_order"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_description_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_key: Mapped[str | None] = mapped_column(String(100))
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    job_description: Mapped[JobDescription] = relationship(back_populates="requirements")


class MatchAnalysis(TimestampedModel, Base):
    """One reproducible rule-based comparison of a resume version to a job posting."""

    __tablename__ = "match_analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    strategy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="completed", nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    required_score: Mapped[int] = mapped_column(Integer, nullable=False)
    bonus_score: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped[Job] = relationship(back_populates="analyses")
    evidences: Mapped[list[MatchEvidence]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    gaps: Mapped[list[MatchGap]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class MatchEvidence(TimestampedModel, Base):
    """A snapshot of the resume chunk that supports one matched requirement."""

    __tablename__ = "match_evidence"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    match_analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_analyses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    jd_requirement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jd_requirements.id", ondelete="SET NULL"), nullable=True
    )
    document_chunk_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True
    )
    relation_type: Mapped[str] = mapped_column(String(30), default="matched", nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)

    analysis: Mapped[MatchAnalysis] = relationship(back_populates="evidences")


class MatchGap(TimestampedModel, Base):
    """A requirement with no explicit supporting text in the selected resume."""

    __tablename__ = "match_gaps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    match_analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_analyses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    jd_requirement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jd_requirements.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    analysis: Mapped[MatchAnalysis] = relationship(back_populates="gaps")


class ResumeTailoringTask(TimestampedModel, Base):
    """A user-controlled tailoring workflow based on one saved match analysis."""

    __tablename__ = "resume_tailoring_tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_analysis_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_analyses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_resume_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    finalized_resume_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)

    suggestions: Mapped[list[ResumeTailoringSuggestion]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class ResumeTailoringSuggestion(TimestampedModel, Base):
    """A safe prompt for user-confirmed resume text; it never asserts an unverified fact."""

    __tablename__ = "resume_tailoring_suggestions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("resume_tailoring_tasks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_gap_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("match_gaps.id", ondelete="SET NULL"), nullable=True
    )
    suggestion_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    confirmed_text: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    task: Mapped[ResumeTailoringTask] = relationship(back_populates="suggestions")
