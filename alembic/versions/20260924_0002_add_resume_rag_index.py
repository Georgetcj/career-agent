"""Add parsed-resume indexing state and pgvector document chunks.

Revision ID: 20260924_0002
Revises: 20260924_0001
Create Date: 2026-09-24 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260924_0002"
down_revision: str | Sequence[str] | None = "20260924_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add durable parse/index status and the source-traceable vector table."""

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "resume_versions",
        sa.Column("index_status", sa.String(length=30), server_default="pending", nullable=False),
    )
    op.add_column("resume_versions", sa.Column("parse_error", sa.Text(), nullable=True))
    op.add_column("resume_versions", sa.Column("index_error", sa.Text(), nullable=True))
    op.add_column(
        "resume_versions", sa.Column("parser_version", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "resume_versions", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section_title", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding", sa.TEXT(), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(["resume_version_id"], ["resume_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "resume_version_id", "chunk_index", name="uq_document_chunks_version_index"
        ),
    )
    op.execute(
        "ALTER TABLE document_chunks ALTER COLUMN embedding "
        "TYPE vector(1536) USING embedding::vector"
    )
    op.create_index(
        op.f("ix_document_chunks_user_id"), "document_chunks", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_document_chunks_resume_version_id"),
        "document_chunks",
        ["resume_version_id"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Remove the RAG data schema and its related version state."""

    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.drop_table("document_chunks")
    op.drop_column("resume_versions", "indexed_at")
    op.drop_column("resume_versions", "parser_version")
    op.drop_column("resume_versions", "index_error")
    op.drop_column("resume_versions", "parse_error")
    op.drop_column("resume_versions", "index_status")
