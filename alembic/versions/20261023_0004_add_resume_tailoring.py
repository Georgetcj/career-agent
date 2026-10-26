"""Add user-confirmed resume tailoring tasks and suggestions.

Revision ID: 20261023_0004
Revises: 20261023_0003
Create Date: 2026-10-23 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261023_0004"
down_revision: str | Sequence[str] | None = "20261023_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    """Persist suggestions separately from their user confirmation decisions."""
    op.create_table(
        "resume_tailoring_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("match_analysis_id", sa.Uuid(), nullable=False),
        sa.Column("source_resume_version_id", sa.Uuid(), nullable=False),
        sa.Column("finalized_resume_version_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_analysis_id"], ["match_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["finalized_resume_version_id"], ["resume_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finalized_resume_version_id"),
    )
    for column in ("user_id", "match_analysis_id", "source_resume_version_id"):
        op.create_index(
            f"ix_resume_tailoring_tasks_{column}", "resume_tailoring_tasks", [column], unique=False
        )
    op.create_table(
        "resume_tailoring_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("match_gap_id", sa.Uuid(), nullable=True),
        sa.Column("suggestion_type", sa.String(length=50), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("proposed_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("confirmed_text", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["task_id"], ["resume_tailoring_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_gap_id"], ["match_gaps.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resume_tailoring_suggestions_task_id",
        "resume_tailoring_suggestions",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove phase-six tables without changing historical resume versions."""
    op.drop_table("resume_tailoring_suggestions")
    op.drop_table("resume_tailoring_tasks")
