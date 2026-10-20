import importlib

from fastapi.testclient import TestClient


def client_with_test_settings(monkeypatch):
    # Configure only while the app module is first imported. Do not set these
    # variables at workflow scope: config unit tests must be able to verify that
    # missing environment variables are rejected.
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/pybasics-smoke-test.db")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
    monkeypatch.setenv("CODE_EXECUTION_ENABLED", "false")
    main = importlib.import_module("app.main")
    return TestClient(main.app)


def test_health_endpoint_reports_process_liveness(monkeypatch):
    with client_with_test_settings(monkeypatch) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_frontend_html(monkeypatch):
    with client_with_test_settings(monkeypatch) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>PyBasics</title>" in response.text
    assert "/assets/app.js" in response.text


def test_frontend_assets_are_served(monkeypatch):
    with client_with_test_settings(monkeypatch) as client:
        script = client.get("/assets/app.js")
        stylesheet = client.get("/assets/style.css")

    assert script.status_code == 200
    assert script.text.strip()
    assert stylesheet.status_code == 200
    assert stylesheet.text.strip()
