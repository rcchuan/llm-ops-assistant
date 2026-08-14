from app.main import app
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)


def test_health_reports_configuration_without_external_requests(monkeypatch) -> None:
    def reject_external_client(*_args, **_kwargs):
        raise AssertionError("health endpoint must not create Dify clients")

    monkeypatch.setattr("app.api.v1.health.check_database", lambda: True)
    monkeypatch.setattr("app.integrations.dify.client.DifyClient.__init__", reject_external_client)
    monkeypatch.setattr("app.integrations.dify.dataset_client.DifyDatasetClient.__init__", reject_external_client)
    monkeypatch.setattr("app.api.v1.health.get_settings", lambda: type("S", (), {
        "app_name": "svc", "app_version": "1", "dify_base_url": "https://secret-dify.example", "dify_app_api_key": type("K", (), {"get_secret_value": lambda self: "secret-app-key-value"})(), "dify_dataset_api_key": type("K", (), {"get_secret_value": lambda self: "secret-dataset-key-value"})(), "dify_dataset_id": "secret-dataset-id-value"
    })())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["dify_app"] == {"status": "configured"}
    assert response.json()["dify_dataset"] == {"status": "configured"}
    assert "https://secret-dify.example" not in response.text
    assert "secret-app-key-value" not in response.text
    assert "secret-dataset-key-value" not in response.text
    assert "secret-dataset-id-value" not in response.text


def test_missing_dify_configuration_does_not_degrade_health(monkeypatch) -> None:
    monkeypatch.setattr("app.api.v1.health.check_database", lambda: True)
    monkeypatch.setattr("app.api.v1.health.get_settings", lambda: type("S", (), {
        "app_name": "svc", "app_version": "1", "dify_base_url": "https://dify", "dify_app_api_key": type("K", (), {"get_secret_value": lambda self: ""})(), "dify_dataset_api_key": type("K", (), {"get_secret_value": lambda self: ""})(), "dify_dataset_id": ""
    })())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["dify_app"]["status"] == "not_configured"
    assert response.json()["dify_dataset"]["status"] == "not_configured"


@pytest.mark.parametrize("base_url", ["", "   "])
def test_blank_dify_base_url_marks_both_services_not_configured(
    monkeypatch, base_url: str
) -> None:
    monkeypatch.setattr("app.api.v1.health.check_database", lambda: True)
    monkeypatch.setattr("app.api.v1.health.get_settings", lambda: type("S", (), {
        "app_name": "svc", "app_version": "1", "dify_base_url": base_url,
        "dify_app_api_key": type("K", (), {"get_secret_value": lambda self: "secret-app-key"})(),
        "dify_dataset_api_key": type("K", (), {"get_secret_value": lambda self: "secret-dataset-key"})(),
        "dify_dataset_id": "secret-dataset-id",
    })())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["dify_app"] == {"status": "not_configured"}
    assert response.json()["dify_dataset"] == {"status": "not_configured"}
    assert "secret-app-key" not in response.text
    assert "secret-dataset-key" not in response.text
    assert "secret-dataset-id" not in response.text
