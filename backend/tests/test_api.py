"""Synthetic smoke tests; no real documents or external providers."""

import pytest
from fastapi.testclient import TestClient

from trapline_api.app import create_app
from trapline_api.config import Settings


def test_health_contract() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok", "service": "trapline-api", "version": "2.0.0-dev"
        }


def test_no_database_or_provider_routes_yet() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/investigations").status_code == 404
        assert client.post("/api/v1/documents").status_code == 404


def test_cors_only_approved_local_origins() -> None:
    with TestClient(create_app()) as client:
        approved = client.options(
            "/api/v1/health",
            headers={"Origin": "http://localhost:8765", "Access-Control-Request-Method": "GET"},
        )
        assert approved.headers["access-control-allow-origin"] == "http://localhost:8765"
        rejected = client.options(
            "/api/v1/health",
            headers={"Origin": "https://attacker.example", "Access-Control-Request-Method": "GET"},
        )
        assert "access-control-allow-origin" not in rejected.headers


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10", "::", "example.org", "localhost"])
def test_non_numeric_or_non_loopback_host_rejected(host: str) -> None:
    with pytest.raises(ValueError):
        Settings(host=host)


def test_loopback_defaults_and_validation() -> None:
    assert Settings().host == "127.0.0.1"
    assert Settings(host="::1").host == "::1"
    with pytest.raises(ValueError):
        Settings(port=0)
