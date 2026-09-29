"""Integration coverage for MinIO-backed source-file upload and access."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from minio.error import S3Error
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from career_agent.api.main import app
from career_agent.api.routers import candidates as candidates_router
from career_agent.infrastructure.database import create_database_engine
from career_agent.infrastructure.object_storage import MinioObjectStorage


def test_resume_upload_and_download_url_round_trip() -> None:
    """A PDF upload creates matching PostgreSQL metadata and a MinIO object."""

    email = f"upload-{uuid4()}@example.com"
    client = TestClient(app)
    storage = MinioObjectStorage()
    object_key: str | None = None

    try:
        user_response = client.post("/users", json={"email": email})
        assert user_response.status_code == 201
        user_id = user_response.json()["id"]

        upload_response = client.post(
            f"/users/{user_id}/resumes/upload",
            data={"title": "后端开发简历", "is_primary": "true"},
            files={"file": ("resume.pdf", b"%PDF-1.4\nminimal test document", "application/pdf")},
        )
        assert upload_response.status_code == 201
        uploaded = upload_response.json()
        assert uploaded["resume"]["title"] == "后端开发简历"
        assert uploaded["version"]["source_format"] == "pdf"
        assert uploaded["version"]["source"]["original_filename"] == "resume.pdf"
        assert len(uploaded["version"]["source"]["sha256"]) == 64
        object_key = uploaded["version"]["source"]["object_key"]
        assert object_key is not None
        storage._client.stat_object(storage.bucket_name, object_key)

        download_response = client.get(
            f"/users/{user_id}/resume-versions/{uploaded['version']['id']}/download-url"
        )
        assert download_response.status_code == 200
        assert download_response.json()["expires_in_seconds"] == 300
        assert "X-Amz-" in download_response.json()["download_url"]

        denied_response = client.get(
            f"/users/{uuid4()}/resume-versions/{uploaded['version']['id']}/download-url"
        )
        assert denied_response.status_code == 404
    finally:
        if object_key is not None:
            storage.remove_object(object_key)
        with create_database_engine().begin() as connection:
            connection.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})


def test_resume_upload_rejects_an_unsupported_file_type() -> None:
    """The upload endpoint rejects formats before creating an object or metadata."""

    email = f"invalid-upload-{uuid4()}@example.com"
    client = TestClient(app)
    try:
        user_response = client.post("/users", json={"email": email})
        user_id = user_response.json()["id"]
        response = client.post(
            f"/users/{user_id}/resumes/upload",
            files={"file": ("resume.exe", b"not a resume", "application/octet-stream")},
        )
        assert response.status_code == 415
    finally:
        with create_database_engine().begin() as connection:
            connection.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})


def test_database_failure_compensates_by_removing_the_uploaded_minio_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed metadata transaction leaves no known MinIO object behind."""

    email = f"compensation-{uuid4()}@example.com"
    client = TestClient(app)
    storage = MinioObjectStorage()
    resume_id = uuid4()
    version_id = uuid4()
    generated_ids = iter([resume_id, version_id])
    object_key: str | None = None

    try:
        user_response = client.post("/users", json={"email": email})
        user_id = user_response.json()["id"]
        object_key = f"resumes/{user_id}/{resume_id}/v1/original.pdf"
        monkeypatch.setattr(candidates_router, "uuid4", lambda: next(generated_ids))

        def fail_commit(_: Session) -> None:
            raise SQLAlchemyError("forced database failure")

        monkeypatch.setattr(Session, "commit", fail_commit)
        response = client.post(
            f"/users/{user_id}/resumes/upload",
            files={"file": ("resume.pdf", b"%PDF-1.4\nrollback test", "application/pdf")},
        )
        assert response.status_code == 500
        with pytest.raises(S3Error):
            storage._client.stat_object(storage.bucket_name, object_key)
    finally:
        with create_database_engine().begin() as connection:
            connection.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
