"""Build safe suggestions and create a new resume version only after user confirmation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from career_agent.infrastructure.models import (
    MatchAnalysis,
    Resume,
    ResumeTailoringSuggestion,
    ResumeTailoringTask,
    ResumeVersion,
)


class ResumeTailoringError(Exception):
    """Raised for unsafe or incomplete tailoring workflow transitions."""


class ResumeTailoringService:
    """Own the task, confirmation, and immutable-version creation workflow."""

    def create_task(
        self, session: Session, user_id: UUID, analysis_id: UUID
    ) -> ResumeTailoringTask:
        analysis = session.scalar(
            select(MatchAnalysis)
            .options(selectinload(MatchAnalysis.gaps))
            .where(MatchAnalysis.id == analysis_id, MatchAnalysis.user_id == user_id)
        )
        if analysis is None:
            raise ResumeTailoringError("Match analysis was not found.")
        task = ResumeTailoringTask(
            user_id=user_id,
            match_analysis_id=analysis.id,
            source_resume_version_id=analysis.resume_version_id,
        )
        for gap in analysis.gaps:
            task.suggestions.append(
                ResumeTailoringSuggestion(
                    match_gap_id=gap.id,
                    suggestion_type="user_confirmed_gap",
                    rationale=gap.description,
                    proposed_text=(
                        "Only if this is true in your real experience, write a concise, "
                        "verifiable resume statement that addresses this requirement. "
                        "Do not add skills, projects, "
                        "or outcomes you cannot personally confirm."
                    ),
                )
            )
        session.add(task)
        session.commit()
        return task

    def decide_suggestion(
        self,
        session: Session,
        user_id: UUID,
        suggestion_id: UUID,
        decision: str,
        confirmed_text: str | None,
    ) -> ResumeTailoringSuggestion:
        suggestion = session.scalar(
            select(ResumeTailoringSuggestion)
            .join(ResumeTailoringTask)
            .where(
                ResumeTailoringSuggestion.id == suggestion_id,
                ResumeTailoringTask.user_id == user_id,
            )
        )
        if suggestion is None:
            raise ResumeTailoringError("Tailoring suggestion was not found.")
        if suggestion.task.status == "finalized":
            raise ResumeTailoringError("A finalized tailoring task cannot be changed.")
        if decision == "accepted" and not confirmed_text:
            raise ResumeTailoringError("Accepted suggestions require user-confirmed resume text.")
        suggestion.status = decision
        suggestion.confirmed_text = confirmed_text.strip() if confirmed_text is not None else None
        suggestion.decided_at = datetime.now(UTC)
        session.commit()
        return suggestion

    def finalize_task(self, session: Session, user_id: UUID, task_id: UUID) -> ResumeTailoringTask:
        task = session.scalar(
            select(ResumeTailoringTask)
            .options(selectinload(ResumeTailoringTask.suggestions))
            .where(ResumeTailoringTask.id == task_id, ResumeTailoringTask.user_id == user_id)
        )
        if task is None:
            raise ResumeTailoringError("Tailoring task was not found.")
        if task.status == "finalized":
            raise ResumeTailoringError("This tailoring task has already been finalized.")
        accepted = [
            item for item in task.suggestions if item.status == "accepted" and item.confirmed_text
        ]
        if not accepted:
            raise ResumeTailoringError(
                "Accept at least one suggestion with user-confirmed text first."
            )
        source = session.scalar(
            select(ResumeVersion)
            .join(Resume)
            .where(ResumeVersion.id == task.source_resume_version_id, Resume.user_id == user_id)
        )
        if source is None or not source.content_text:
            raise ResumeTailoringError(
                "The source resume text is unavailable for version creation."
            )
        next_number = (
            session.scalar(
                select(func.max(ResumeVersion.version_number)).where(
                    ResumeVersion.resume_id == source.resume_id
                )
            )
            or 0
        ) + 1
        additions = "\n".join(f"- {item.confirmed_text}" for item in accepted)
        content = f"{source.content_text.rstrip()}\n\n用户确认的岗位定制补充\n{additions}\n"
        session.execute(
            update(ResumeVersion)
            .where(ResumeVersion.resume_id == source.resume_id)
            .values(is_current=False)
        )
        version = ResumeVersion(
            resume_id=source.resume_id,
            version_number=next_number,
            content_text=content,
            source_format="text",
            parse_status="user_confirmed",
            index_status="pending",
            is_current=True,
        )
        session.add(version)
        session.flush()
        task.finalized_resume_version_id = version.id
        task.status = "finalized"
        session.commit()
        return task
