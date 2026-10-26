"""Integration coverage for user-confirmed, immutable resume tailoring."""

from uuid import uuid4

from fastapi.testclient import TestClient

from career_agent.api.main import app
from career_agent.infrastructure.document_parser import ParsedDocument


class FakeStorage:
    def get_object_bytes(self, object_key: str) -> bytes:
        assert object_key == "resumes/tailoring.pdf"
        return b"fixture"


class FakeParser:
    def parse(self, source_format: str, payload: bytes) -> ParsedDocument:
        assert source_format == "pdf"
        return ParsedDocument(content="项目经历：使用 Python 和 FastAPI 构建服务。", page_count=1)


class FakeEmbeddings:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, *([0.0] * 1535)] for _ in texts]


def test_tailoring_requires_user_confirmation_and_creates_new_version(monkeypatch) -> None:
    """A gap becomes a suggestion, never a resume claim until the user supplies text."""

    import career_agent.services.resume_indexing as indexing_service

    monkeypatch.setattr(indexing_service, "MinioObjectStorage", FakeStorage)
    monkeypatch.setattr(indexing_service, "ResumeDocumentParser", FakeParser)
    monkeypatch.setattr(indexing_service, "OpenAICompatibleEmbeddingClient", FakeEmbeddings)
    client = TestClient(app)
    user_id = client.post("/users", json={"email": f"tailor-{uuid4()}@example.com"}).json()["id"]
    other_user_id = client.post(
        "/users", json={"email": f"tailor-other-{uuid4()}@example.com"}
    ).json()["id"]
    resume_id = client.post(
        f"/users/{user_id}/resumes", json={"title": "原始简历", "is_primary": True}
    ).json()["id"]
    source_version_id = client.post(
        f"/resumes/{resume_id}/versions",
        json={
            "source_format": "pdf",
            "source": {"object_key": "resumes/tailoring.pdf", "original_filename": "tailoring.pdf"},
        },
    ).json()["id"]
    assert (
        client.post(f"/users/{user_id}/resume-versions/{source_version_id}/index").status_code
        == 200
    )
    job_id = client.post(
        f"/users/{user_id}/jobs",
        json={"title": "后端工程师", "raw_description": "要求 Python、FastAPI 和 Redis 经验。"},
    ).json()["id"]
    assert client.post(f"/users/{user_id}/jobs/{job_id}/parse").status_code == 200
    analysis_id = client.post(f"/users/{user_id}/jobs/{job_id}/match", json={}).json()["id"]

    task = client.post(f"/users/{user_id}/match-analyses/{analysis_id}/tailoring-tasks")
    assert task.status_code == 201
    task_payload = task.json()
    suggestion_id = task_payload["suggestions"][0]["id"]
    assert task_payload["suggestions"][0]["status"] == "pending"
    assert (
        client.post(f"/users/{user_id}/tailoring-tasks/{task_payload['id']}/finalize").status_code
        == 422
    )
    assert (
        client.patch(
            f"/users/{user_id}/tailoring-suggestions/{suggestion_id}", json={"decision": "accepted"}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/users/{other_user_id}/tailoring-suggestions/{suggestion_id}",
            json={"decision": "rejected"},
        ).status_code
        == 404
    )

    confirmed = "在真实项目中使用 Redis 实现缓存与热点数据加速。"
    accepted = client.patch(
        f"/users/{user_id}/tailoring-suggestions/{suggestion_id}",
        json={"decision": "accepted", "confirmed_text": confirmed},
    )
    assert accepted.status_code == 200
    finalized = client.post(f"/users/{user_id}/tailoring-tasks/{task_payload['id']}/finalize")
    assert finalized.status_code == 200
    new_version_id = finalized.json()["resume_version_id"]
    versions = client.get(f"/resumes/{resume_id}/versions").json()
    assert len(versions) == 2
    old_version = next(item for item in versions if item["id"] == source_version_id)
    new_version = next(item for item in versions if item["id"] == new_version_id)
    assert old_version["is_current"] is False
    assert new_version["is_current"] is True
    assert confirmed in new_version["content_text"]
