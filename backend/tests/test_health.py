from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_database_up(monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.health.check_database", lambda: True)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "llm-ops-assistant-backend",
        "version": "0.3.0",
        "database": {"status": "up"},
        "api": {"status": "up"},
        "dify_app": {"status": "configured"},
        "dify_dataset": {"status": "configured"},
    }


def test_health_database_down(monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.health.check_database", lambda: False)

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "service": "llm-ops-assistant-backend",
        "version": "0.3.0",
        "database": {"status": "down"},
        "api": {"status": "up"},
        "dify_app": {"status": "configured"},
        "dify_dataset": {"status": "configured"},
    }
    assert "password" not in response.text.lower()
