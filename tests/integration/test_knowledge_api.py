"""Integration coverage for explicit indexing and permission-scoped vector retrieval."""

from uuid import uuid4

from fastapi.testclient import TestClient

from career_agent.api.main import app
from career_agent.infrastructure.document_parser import ParsedDocument


class FakeStorage:
    """Avoid a network read while retaining the indexing service's boundary."""

    def get_object_bytes(self, object_key: str) -> bytes:
        assert object_key == "resumes/test.pdf"
        return b"not used by the fake parser"


class FakeParser:
    """Provide parser output without needing a fixture file."""

    def parse(self, source_format: str, payload: bytes) -> ParsedDocument:
        assert source_format == "pdf"
        return ParsedDocument(
            content="技能\nPython FastAPI PostgreSQL\n项目经历\n构建了候选人检索服务。",
            page_count=1,
        )


class FakeEmbeddings:
    """Return valid 1536-dimensional vectors without contacting the configured provider."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, *([0.0] * 1535)] for _ in texts]


def test_index_and_search_resume_chunks_without_external_api(monkeypatch) -> None:
    """Indexing stores source-traceable chunks and search remains within the supplied user."""

    import career_agent.api.routers.knowledge as knowledge_router
    import career_agent.services.resume_indexing as indexing_service

    monkeypatch.setattr(indexing_service, "MinioObjectStorage", FakeStorage)
    monkeypatch.setattr(indexing_service, "ResumeDocumentParser", FakeParser)
    monkeypatch.setattr(indexing_service, "OpenAICompatibleEmbeddingClient", FakeEmbeddings)
    monkeypatch.setattr(knowledge_router, "OpenAICompatibleEmbeddingClient", FakeEmbeddings)

    client = TestClient(app)
    user_id = client.post("/users", json={"email": f"rag-{uuid4()}@example.com"}).json()["id"]
    resume_id = client.post(f"/users/{user_id}/resumes", json={"title": "RAG 测试简历"}).json()[
        "id"
    ]
    version = client.post(
        f"/resumes/{resume_id}/versions",
        json={
            "source_format": "pdf",
            "source": {"object_key": "resumes/test.pdf", "original_filename": "test.pdf"},
        },
    )
    assert version.status_code == 201
    version_id = version.json()["id"]

    indexed = client.post(f"/users/{user_id}/resume-versions/{version_id}/index")
    assert indexed.status_code == 200
    assert indexed.json()["parse_status"] == "parsed"
    assert indexed.json()["index_status"] == "indexed"
    assert indexed.json()["chunk_count"] >= 1

    searched = client.post(
        f"/users/{user_id}/knowledge/search", json={"query": "Python 后端项目", "limit": 5}
    )
    assert searched.status_code == 200
    result = searched.json()["results"][0]
    assert result["resume_version_id"] == version_id
    assert "Python" in result["content"]
