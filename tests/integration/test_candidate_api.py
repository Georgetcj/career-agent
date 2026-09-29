"""Integration coverage for persisted candidate and resume metadata endpoints."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from career_agent.api.main import app
from career_agent.infrastructure.database import create_database_engine


def test_candidate_and_resume_metadata_round_trip() -> None:
    """The API writes and reads the first MVP data model through PostgreSQL."""

    email = f"candidate-{uuid4()}@example.com"
    client = TestClient(app)

    try:
        created_user = client.post("/users", json={"email": email})
        assert created_user.status_code == 201
        user = created_user.json()
        user_id = user["id"]
        assert user["email"] == email

        profile_response = client.put(
            f"/users/{user_id}/profile",
            json={"full_name": "测试候选人", "target_role": "后端开发", "years_of_experience": 1},
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["target_role"] == "后端开发"

        preference_response = client.put(
            f"/users/{user_id}/preferences",
            json={"preferred_industries": ["互联网"], "job_type": "full-time"},
        )
        assert preference_response.status_code == 200
        assert preference_response.json()["preferred_industries"] == ["互联网"]

        created_resume = client.post(
            f"/users/{user_id}/resumes",
            json={"title": "后端开发简历", "is_primary": True},
        )
        assert created_resume.status_code == 201
        resume_id = created_resume.json()["id"]

        created_version = client.post(
            f"/resumes/{resume_id}/versions",
            json={
                "source_format": "pdf",
                "content_text": "Python、FastAPI、PostgreSQL",
                "source": {"object_key": "resumes/test.pdf", "original_filename": "test.pdf"},
            },
        )
        assert created_version.status_code == 201
        assert created_version.json()["version_number"] == 1
        assert created_version.json()["source"]["storage_provider"] == "minio"

        versions = client.get(f"/resumes/{resume_id}/versions")
        assert versions.status_code == 200
        assert len(versions.json()) == 1
    finally:
        with create_database_engine().begin() as connection:
            connection.execute(text("DELETE FROM users WHERE email = :email"), {"email": email})
