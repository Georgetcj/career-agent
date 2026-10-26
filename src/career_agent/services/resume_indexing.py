"""Parse, chunk, embed, and persist one user-owned resume version."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from career_agent.core.config import get_settings
from career_agent.infrastructure.document_parser import (
    DocumentParsingError,
    ParsedDocument,
    ResumeDocumentParser,
)
from career_agent.infrastructure.embeddings import EmbeddingError, OpenAICompatibleEmbeddingClient
from career_agent.infrastructure.models import DocumentChunk, Resume, ResumeVersion
from career_agent.infrastructure.object_storage import MinioObjectStorage, ObjectStorageError


class ResumeIndexingError(Exception):
    """Raised when a resume cannot safely reach the indexed state."""


@dataclass(frozen=True)
class TextChunk:
    """A deterministic, source-order-preserving text segment."""

    chunk_index: int
    content: str
    section_title: str | None


def split_resume_text(content: str, chunk_size: int, overlap: int) -> list[TextChunk]:
    """Split on paragraph boundaries first, with fixed-size fallback for long paragraphs."""

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Chunk overlap must be non-negative and smaller than the chunk size.")

    paragraphs = [part.strip() for part in content.split("\n") if part.strip()]
    raw_chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                raw_chunks.append(current)
                current = ""
            start = 0
            step = chunk_size - overlap
            while start < len(paragraph):
                raw_chunks.append(paragraph[start : start + chunk_size])
                start += step
            continue
        candidate = paragraph if not current else f"{current}\n{paragraph}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        raw_chunks.append(current)
        current = paragraph
    if current:
        raw_chunks.append(current)

    chunks: list[TextChunk] = []
    current_title: str | None = None
    for index, chunk in enumerate(raw_chunks):
        first_line = chunk.split("\n", maxsplit=1)[0]
        if len(first_line) <= 40 and re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9 /&+().-]+", first_line):
            current_title = first_line
        chunks.append(TextChunk(chunk_index=index, content=chunk, section_title=current_title))
    return chunks


class ResumeIndexingService:
    """Keep state transitions and replacement indexing behavior in one unit of work."""

    def index_resume_version(
        self, session: Session, user_id: UUID, version_id: UUID
    ) -> ResumeVersion:
        version = session.scalar(
            select(ResumeVersion)
            .options(selectinload(ResumeVersion.source))
            .join(Resume)
            .where(ResumeVersion.id == version_id, Resume.user_id == user_id)
        )
        if version is None:
            raise ResumeIndexingError("Resume version was not found.")
        if version.source is None and not (
            version.content_text and version.source_format in {"text", "markdown"}
        ):
            raise ResumeIndexingError(
                "Resume version has no uploaded source file or confirmed text."
            )

        version.parse_status = "parsing"
        version.index_status = "pending"
        version.parse_error = None
        version.index_error = None
        session.commit()

        try:
            if version.source is None:
                parsed = ParsedDocument(content=version.content_text or "", page_count=None)
            else:
                source_bytes = MinioObjectStorage().get_object_bytes(version.source.object_key)
                parsed = ResumeDocumentParser().parse(version.source_format, source_bytes)
        except (ObjectStorageError, DocumentParsingError) as error:
            version.parse_status = "failed"
            version.parse_error = str(error)
            session.commit()
            raise ResumeIndexingError("Resume parsing failed.") from error

        version.content_text = parsed.content
        version.parse_status = "parsed"
        version.parse_error = None
        version.parser_version = "resume-parser-v1"
        version.index_status = "indexing"
        session.commit()

        settings = get_settings()
        chunks = split_resume_text(
            parsed.content, settings.rag_chunk_size_chars, settings.rag_chunk_overlap_chars
        )
        try:
            client = OpenAICompatibleEmbeddingClient()
            vectors: list[list[float]] = []
            for start in range(0, len(chunks), settings.embedding_batch_size):
                batch = chunks[start : start + settings.embedding_batch_size]
                vectors.extend(client.embed([chunk.content for chunk in batch]))
        except EmbeddingError as error:
            version.index_status = "failed"
            version.index_error = str(error)
            session.commit()
            raise ResumeIndexingError("Resume embedding failed.") from error

        session.execute(delete(DocumentChunk).where(DocumentChunk.resume_version_id == version.id))
        session.add_all(
            [
                DocumentChunk(
                    user_id=user_id,
                    resume_version_id=version.id,
                    chunk_index=chunk.chunk_index,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    content_hash=hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
                    metadata_={
                        "page_count": parsed.page_count,
                        "source_format": version.source_format,
                    },
                    embedding=vector,
                    embedding_model=settings.embedding_model,
                    embedding_dimensions=settings.embedding_dimensions,
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
        )
        version.index_status = "indexed"
        version.index_error = None
        version.indexed_at = datetime.now(UTC)
        session.commit()
        session.refresh(version)
        return version
