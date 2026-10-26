"""Add manually supplied jobs and explainable resume-match records.

Revision ID: 20261023_0003
Revises: 20260924_0002
Create Date: 2026-10-23 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261023_0003"
down_revision: str | Sequence[str] | None = "20260924_0002"
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
    """Create job, extracted requirement, match evidence, and gap tables."""

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("company_name", sa.String(length=200)),
        sa.Column("city", sa.String(length=100)),
        sa.Column("source_url", sa.String(length=1000)),
        sa.Column("raw_description", sa.Text(), nullable=False),
        sa.Column("parse_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("parse_error", sa.Text()),
        sa.Column("parsed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)
    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text()),
        *_timestamps(),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_table(
        "jd_requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_description_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("normalized_key", sa.String(length=100)),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["job_description_id"], ["job_descriptions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_description_id", "ordinal", name="uq_jd_requirements_description_order"
        ),
    )
    op.create_index(
        op.f("ix_jd_requirements_job_description_id"),
        "jd_requirements",
        ["job_description_id"],
        unique=False,
    )
    op.create_table(
        "match_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("required_score", sa.Integer(), nullable=False),
        sa.Column("bonus_score", sa.Integer(), nullable=False),
        sa.Column("evidence_score", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "job_id", "resume_version_id"):
        op.create_index(f"ix_match_analyses_{column}", "match_analyses", [column], unique=False)
    for table_name, parent_column, parent_table in (
        ("match_evidence", "match_analysis_id", "match_analyses"),
        ("match_gaps", "match_analysis_id", "match_analyses"),
    ):
        columns = [
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column(parent_column, sa.Uuid(), nullable=False),
            sa.Column("jd_requirement_id", sa.Uuid(), nullable=True),
        ]
        if table_name == "match_evidence":
            columns += [
                sa.Column("document_chunk_id", sa.Uuid(), nullable=True),
                sa.Column("relation_type", sa.String(length=30), nullable=False),
                sa.Column("evidence_text", sa.Text(), nullable=False),
            ]
        else:
            columns += [
                sa.Column("category", sa.String(length=30), nullable=False),
                sa.Column("severity", sa.String(length=30), nullable=False),
                sa.Column("description", sa.Text(), nullable=False),
            ]
        op.create_table(
            table_name,
            *columns,
            *_timestamps(),
            sa.ForeignKeyConstraint([parent_column], [f"{parent_table}.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["jd_requirement_id"], ["jd_requirements.id"], ondelete="SET NULL"
            ),
            *(
                [
                    sa.ForeignKeyConstraint(
                        ["document_chunk_id"], ["document_chunks.id"], ondelete="SET NULL"
                    )
                ]
                if table_name == "match_evidence"
                else []
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            f"ix_{table_name}_{parent_column}", table_name, [parent_column], unique=False
        )


def downgrade() -> None:
    """Remove the phase-five job matching schema in dependency order."""
    op.drop_table("match_gaps")
    op.drop_table("match_evidence")
    op.drop_table("match_analyses")
    op.drop_table("jd_requirements")
    op.drop_table("job_descriptions")
    op.drop_table("jobs")
