"""Deterministic JD parsing and evidence-grounded first-pass job matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from career_agent.infrastructure.models import (
    DocumentChunk,
    JDRequirement,
    Job,
    JobDescription,
    MatchAnalysis,
    MatchEvidence,
    MatchGap,
    Resume,
    ResumeVersion,
)

PARSER_VERSION = "jd-rule-v1"
MATCH_STRATEGY_VERSION = "resume-keyword-evidence-v1"
SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "fastapi": ("fastapi",),
    "django": ("django",),
    "flask": ("flask",),
    "java": ("java",),
    "go": ("golang", "go"),
    "sql": ("sql",),
    "postgresql": ("postgresql", "postgres"),
    "mysql": ("mysql",),
    "redis": ("redis",),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "linux": ("linux",),
    "git": ("git",),
    "kafka": ("kafka",),
    "rabbitmq": ("rabbitmq",),
    "mongodb": ("mongodb",),
    "elasticsearch": ("elasticsearch",),
    "celery": ("celery",),
    "rag": ("rag",),
    "langchain": ("langchain",),
    "pytorch": ("pytorch",),
    "tensorflow": ("tensorflow",),
}
BONUS_MARKERS = ("加分", "优先", "bonus", "preferred", "nice to have", "nice-to-have")


class JobMatchingError(Exception):
    """Raised when a match cannot be run from the user's current data."""


@dataclass(frozen=True)
class ParsedRequirement:
    category: str
    text: str
    normalized_key: str | None
    is_required: bool


def _contains_alias(text: str, alias: str) -> bool:
    if alias.isascii() and alias.replace("-", "").isalnum():
        return (
            re.search(rf"(?<![A-Za-z0-9_]){re.escape(alias)}(?![A-Za-z0-9_])", text, re.I)
            is not None
        )
    return alias.casefold() in text.casefold()


def extract_requirements(raw_description: str) -> list[ParsedRequirement]:
    """Extract known technical skills without claiming LLM-level understanding."""

    requirements: list[ParsedRequirement] = []
    seen_skills: set[str] = set()
    for line in (item.strip(" -•\t") for item in raw_description.splitlines()):
        if not line:
            continue
        is_required = not any(marker in line.casefold() for marker in BONUS_MARKERS)
        matched = False
        for skill, aliases in SKILL_ALIASES.items():
            if skill not in seen_skills and any(_contains_alias(line, alias) for alias in aliases):
                requirements.append(ParsedRequirement("skill", line, skill, is_required))
                seen_skills.add(skill)
                matched = True
        if not matched and any(
            marker in line for marker in ("学历", "本科", "硕士", "经验", "职责", "负责")
        ):
            category = "bonus" if not is_required else "hard_requirement"
            requirements.append(ParsedRequirement(category, line, None, is_required))
    return requirements


class JobMatchingService:
    """Owns the explicit parse and match state transitions."""

    def parse_job(self, session: Session, job: Job) -> Job:
        requirements = extract_requirements(job.raw_description)
        job.parse_status = "parsing"
        description = job.description
        if description is None:
            description = JobDescription(job=job, parser_version=PARSER_VERSION)
            session.add(description)
        else:
            description.parser_version = PARSER_VERSION
            description.requirements.clear()
        description.summary = f"Deterministically extracted {len(requirements)} requirement(s)."
        for ordinal, requirement in enumerate(requirements, start=1):
            description.requirements.append(
                JDRequirement(
                    category=requirement.category,
                    requirement_text=requirement.text,
                    normalized_key=requirement.normalized_key,
                    is_required=requirement.is_required,
                    ordinal=ordinal,
                )
            )
        job.parse_status = "parsed"
        job.parse_error = None
        job.parsed_at = datetime.now(UTC)
        session.commit()
        return job

    def _load_resume_version(
        self, session: Session, user_id: UUID, requested_version_id: UUID | None
    ) -> ResumeVersion:
        statement = (
            select(ResumeVersion)
            .join(Resume)
            .where(Resume.user_id == user_id, ResumeVersion.index_status == "indexed")
            .order_by(ResumeVersion.indexed_at.desc())
        )
        if requested_version_id is not None:
            statement = statement.where(ResumeVersion.id == requested_version_id)
        else:
            statement = statement.where(ResumeVersion.is_current.is_(True))
        version = session.scalar(statement)
        if version is None:
            raise JobMatchingError("An indexed current resume version is required before matching.")
        return version

    def run_match(
        self, session: Session, user_id: UUID, job: Job, requested_version_id: UUID | None
    ) -> MatchAnalysis:
        description = session.scalar(
            select(JobDescription)
            .options(selectinload(JobDescription.requirements))
            .where(JobDescription.job_id == job.id)
        )
        if description is None or not description.requirements:
            raise JobMatchingError("Parse the job description before running a match.")
        version = self._load_resume_version(session, user_id, requested_version_id)
        chunks = list(
            session.scalars(
                select(DocumentChunk).where(DocumentChunk.resume_version_id == version.id)
            )
        )
        if not chunks:
            raise JobMatchingError("The selected resume has no indexed source chunks.")

        analysis = MatchAnalysis(
            user_id=user_id,
            job_id=job.id,
            resume_version_id=version.id,
            strategy_version=MATCH_STRATEGY_VERSION,
            status="completed",
            overall_score=0,
            required_score=0,
            bonus_score=0,
            evidence_score=0,
            summary="",
        )
        required_skills = [
            item for item in description.requirements if item.normalized_key and item.is_required
        ]
        bonus_skills = [
            item
            for item in description.requirements
            if item.normalized_key and not item.is_required
        ]
        matched_required = 0
        matched_bonus = 0
        for requirement in description.requirements:
            if requirement.normalized_key is None:
                continue
            evidence_chunk = next(
                (
                    chunk
                    for chunk in chunks
                    if any(
                        _contains_alias(chunk.content, alias)
                        for alias in SKILL_ALIASES[requirement.normalized_key]
                    )
                ),
                None,
            )
            if evidence_chunk is not None:
                analysis.evidences.append(
                    MatchEvidence(
                        jd_requirement_id=requirement.id,
                        document_chunk_id=evidence_chunk.id,
                        evidence_text=evidence_chunk.content,
                    )
                )
                if requirement.is_required:
                    matched_required += 1
                else:
                    matched_bonus += 1
            else:
                analysis.gaps.append(
                    MatchGap(
                        jd_requirement_id=requirement.id,
                        category=requirement.category,
                        severity="required" if requirement.is_required else "bonus",
                        description=(
                            "No explicit resume evidence was found for: "
                            f"{requirement.requirement_text}"
                        ),
                    )
                )
        required_ratio = matched_required / len(required_skills) if required_skills else 1.0
        bonus_ratio = matched_bonus / len(bonus_skills) if bonus_skills else 0.0
        evidence_ratio = len(analysis.evidences) / (len(required_skills) + len(bonus_skills) or 1)
        analysis.required_score = round(required_ratio * 70)
        analysis.bonus_score = round(bonus_ratio * 20)
        analysis.evidence_score = round(evidence_ratio * 10)
        analysis.overall_score = (
            analysis.required_score + analysis.bonus_score + analysis.evidence_score
        )
        analysis.summary = (
            "Found explicit resume evidence for "
            f"{matched_required}/{len(required_skills)} required "
            f"and {matched_bonus}/{len(bonus_skills)} bonus technical requirement(s). "
            "Scores are rule-based and should be reviewed by the user."
        )
        session.add(analysis)
        session.commit()
        return analysis
