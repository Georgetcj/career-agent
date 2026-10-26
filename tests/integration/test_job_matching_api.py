"""Integration coverage for deterministic JD parsing and evidence-grounded matching."""

from uuid import uuid4

from fastapi.testclient import TestClient

from career_agent.api.main import app
from career_agent.infrastructure.document_parser import ParsedDocument


class FakeStorage:
    def get_object_bytes(self, object_key: str) -> bytes:
        assert object_key == "resumes/match.pdf"
        return b"fixture"


class FakeParser:
    def parse(self, source_format: str, payload: bytes) -> ParsedDocument:
        assert source_format == "pdf"
        return ParsedDocument(
            content="项目经历：使用 Python、FastAPI 和 Docker 构建服务。", page_count=1
        )


class FakeEmbeddings:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, *([0.0] * 1535)] for _ in texts]


def test_job_matching_keeps_evidence_and_gaps_within_one_user(monkeypatch) -> None:
    """A match records only explicit chunk evidence and does not leak across users."""

    import career_agent.services.resume_indexing as indexing_service

    monkeypatch.setattr(indexing_service, "MinioObjectStorage", FakeStorage)
    monkeypatch.setattr(indexing_service, "ResumeDocumentParser", FakeParser)
    monkeypatch.setattr(indexing_service, "OpenAICompatibleEmbeddingClient", FakeEmbeddings)
    client = TestClient(app)
    user_id = client.post("/users", json={"email": f"match-{uuid4()}@example.com"}).json()["id"]
    other_user_id = client.post(
        "/users", json={"email": f"other-{uuid4()}@example.com"}
    ).json()["id"]
    resume_id = client.post(
        f"/users/{user_id}/resumes", json={"title": "匹配测试简历", "is_primary": True}
    ).json()["id"]
    version_id = client.post(
        f"/resumes/{resume_id}/versions",
        json={
            "source_format": "pdf",
            "source": {"object_key": "resumes/match.pdf", "original_filename": "match.pdf"},
        },
    ).json()["id"]
    assert client.post(f"/users/{user_id}/resume-versions/{version_id}/index").status_code == 200

    created = client.post(
        f"/users/{user_id}/jobs",
        json={
            "title": "后端工程师",
            "company_name": "示例公司",
            "raw_description": "任职要求：熟悉 Python、FastAPI 和 Redis。\n优先：有 Docker 经验。",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["id"]
    parsed = client.post(f"/users/{user_id}/jobs/{job_id}/parse")
    assert parsed.status_code == 200
    assert {item["normalized_key"] for item in parsed.json()["requirements"]} >= {
        "python",
        "fastapi",
        "redis",
        "docker",
    }

    matched = client.post(f"/users/{user_id}/jobs/{job_id}/match", json={})
    assert matched.status_code == 201
    payload = matched.json()
    assert payload["overall_score"] > 0
    assert any("Python" in item["evidence_text"] for item in payload["evidences"])
    assert any("Redis" in item["description"] for item in payload["gaps"])
    assert client.get(f"/users/{other_user_id}/match-analyses/{payload['id']}").status_code == 404
