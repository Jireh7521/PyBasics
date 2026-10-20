from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_process_liveness():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_frontend_html():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<title>PyBasics</title>' in response.text
    assert '/assets/app.js' in response.text


def test_frontend_assets_are_served():
    with TestClient(app) as client:
        script = client.get("/assets/app.js")
        stylesheet = client.get("/assets/style.css")

    assert script.status_code == 200
    assert script.text.strip()
    assert stylesheet.status_code == 200
    assert stylesheet.text.strip()
