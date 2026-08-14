from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


INDEX_MARKER = "stage-7-test-index"


def make_client(dist_dir: Path) -> TestClient:
    return TestClient(create_app(dist_dir=dist_dir))


def test_without_dist_keeps_api_and_returns_404_for_frontend_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("app.api.v1.health.check_database", lambda: True)

    with make_client(tmp_path / "missing-dist") as client:
        health_response = client.get("/api/v1/health")
        root_response = client.get("/")
        route_response = client.get("/chat")

    assert health_response.status_code == 200
    assert health_response.headers["content-type"].startswith("application/json")
    assert root_response.status_code == 404
    assert root_response.headers["content-type"].startswith("application/json")
    assert route_response.status_code == 404
    assert route_response.headers["content-type"].startswith("application/json")


def test_with_dist_serves_index_for_root_and_frontend_routes(tmp_path: Path) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(
        f"<!doctype html><title>{INDEX_MARKER}</title>",
        encoding="utf-8",
    )

    with make_client(dist_dir) as client:
        root_response = client.get("/")
        route_response = client.get("/work-orders/1")

    for response in (root_response, route_response):
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert INDEX_MARKER in response.text


def test_with_dist_preserves_api_routes_and_never_falls_back_for_api_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text(INDEX_MARKER, encoding="utf-8")
    monkeypatch.setattr("app.api.v1.health.check_database", lambda: True)

    with make_client(dist_dir) as client:
        health_response = client.get("/api/v1/health")
        missing_responses = [
            client.get(path)
            for path in ("/api", "/api/missing", "/api/v1", "/api/v1/missing")
        ]

    assert health_response.status_code == 200
    assert health_response.headers["content-type"].startswith("application/json")
    for response in missing_responses:
        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert INDEX_MARKER not in response.text


def test_with_dist_serves_existing_asset_and_returns_404_for_missing_assets(
    tmp_path: Path,
) -> None:
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text(INDEX_MARKER, encoding="utf-8")
    (assets_dir / "app.js").write_text("window.stage7 = true", encoding="utf-8")

    with make_client(dist_dir) as client:
        asset_response = client.get("/assets/app.js")
        missing_responses = [
            client.get(path) for path in ("/assets", "/assets/", "/assets/missing.js")
        ]

    assert asset_response.status_code == 200
    assert asset_response.headers["content-type"].split(";", 1)[0] in {
        "application/javascript",
        "text/javascript",
    }
    assert "window.stage7 = true" in asset_response.text
    for response in missing_responses:
        assert response.status_code == 404
        assert INDEX_MARKER not in response.text
