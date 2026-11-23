"""Synthetic-only CORS/Host regression tests. TestClient makes no socket calls."""

from fastapi.testclient import TestClient

from trapline_api.app import create_app
from trapline_api.config import Settings


def preflight(client, origin, method="GET", host="localhost:9876"):
    return client.options(
        "/api/v1/health",
        headers={
            "Host": host,
            "Origin": origin,
            "Access-Control-Request-Method": method,
        },
    )


def test_custom_port_allows_only_its_loopback_origins():
    with TestClient(create_app(Settings(port=9876)), base_url="http://localhost:9876") as client:
        for origin in ("http://localhost:9876", "http://127.0.0.1:9876"):
            response = preflight(client, origin)
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
            assert response.headers.get("access-control-allow-credentials") is None

        for origin in (
            "http://localhost:8765",
            "http://localhost:9877",
            "http://localhost.evil.test:9876",
            "https://localhost:9876",
        ):
            response = preflight(client, origin)
            assert response.status_code == 400
            assert "access-control-allow-origin" not in response.headers

        assert preflight(client, "http://localhost:9876", method="POST").status_code == 400
        forged = preflight(client, "http://localhost:9876", host="evil.test")
        assert forged.status_code == 400
        assert "access-control-allow-origin" not in forged.headers


def test_create_app_uses_configured_environment_port(monkeypatch):
    monkeypatch.setenv("TRAPLINE_PORT", "9412")
    with TestClient(create_app(), base_url="http://127.0.0.1:9412") as client:
        response = preflight(client, "http://127.0.0.1:9412", host="127.0.0.1:9412")
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:9412"

        old_port = preflight(client, "http://localhost:8765", host="127.0.0.1:9412")
        assert old_port.status_code == 400
        assert "access-control-allow-origin" not in old_port.headers


def test_default_port_and_health_contract_unchanged(monkeypatch):
    monkeypatch.delenv("TRAPLINE_PORT", raising=False)
    with TestClient(create_app(), base_url="http://localhost:8765") as client:
        assert client.get("/api/v1/health").json() == {
            "status": "ok",
            "service": "trapline-api",
            "version": "2.0.0-dev",
        }
        allowed = preflight(client, "http://localhost:8765", host="localhost:8765")
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:8765"
        assert client.post("/api/v1/documents").status_code == 404
