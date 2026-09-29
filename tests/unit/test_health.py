"""Tests for the API health endpoint."""

from fastapi.testclient import TestClient

from career_agent.api.main import app


def test_health_reports_available_database(monkeypatch) -> None:
    """A successful database probe returns the expected health payload."""

    monkeypatch.setattr("career_agent.api.main.check_database_connection", lambda: None)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "available"}
