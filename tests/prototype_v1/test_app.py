import pytest
from fastapi.testclient import TestClient

from prototype_v1.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_live_returns_prototype_health(client):
    response = client.get("/api/prototype/live")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "ok"
    assert body["app"] == "marawa-prototype-v1"
    assert body["server_generation"]


def test_mutating_request_rejects_cross_site_origin_before_body(client):
    response = client.post(
        "/api/prototype/sessions",
        content=b"not-json",
        headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"


def test_static_response_has_security_headers(client):
    response = client.get("/api/prototype/live")

    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "camera=()" in response.headers["permissions-policy"]


def test_production_environment_is_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    from prototype_v1.config import load_config

    with pytest.raises(ValueError, match="APP_ENV"):
        load_config()

    monkeypatch.delenv("APP_ENV")


def test_loopback_origin_is_allowed_for_session_creation(client):
    response = client.post(
        "/api/prototype/sessions",
        json={},
        headers={"Origin": "http://127.0.0.1:8010"},
    )

    assert response.status_code == 201
    assert response.json()["data"]["state_version"] == 0
