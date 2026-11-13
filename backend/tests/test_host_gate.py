"""Synthetic Host-header security regression tests; no external network."""

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from trapline_api.app import create_app
from trapline_api.host_gate import LocalHostGate, valid_local_authority


@pytest.mark.parametrize("authority", [
    "localhost", "localhost:8765", "127.0.0.1", "127.0.0.1:8765",
    "127.10.20.30:80", "[::1]", "[::1]:8765",
])
def test_valid_loopback_authorities(authority):
    assert valid_local_authority(authority)


@pytest.mark.parametrize("authority", [
    "", "attacker.example", "attacker.example:8765", "localhost.attacker.example",
    "localhost@attacker.example", "LOCALHOST", "localhost:0", "localhost:65536",
    "localhost:-1", "localhost:abc", "localhost:", "localhost:80:90",
    "127.0.0.1.evil", "0.0.0.0", "192.168.1.1", "169.254.169.254",
    "[::]", "[::ffff:127.0.0.1]", "[fe80::1]", "::1", "[::1]evil",
    "[::1]:0", "[::1]:65536", "[::1]:bad", "[::1", "[::1]:80:90",
    "localhost\nX-Test: true", "localhost ", "localhost:８０", "localhost:⁸⁰",
])
def test_invalid_authorities(authority):
    assert not valid_local_authority(authority)


def test_host_gate_in_app():
    with TestClient(create_app(), base_url="http://localhost:8765") as client:
        assert client.get("/api/v1/health", headers={"host": "localhost:8765"}).status_code == 200
        assert client.get("/api/v1/health", headers={"host": "[::1]:8765"}).status_code == 200
        for host in ("evil.example", "localhost.evil.example", "192.168.0.1", "[::]:8765"):
            response = client.get("/api/v1/health", headers={"host": host})
            assert response.status_code == 400
            assert "access-control-allow-origin" not in response.headers
        response = client.options("/api/v1/health", headers={
            "host": "evil.example", "origin": "http://localhost:8765",
            "access-control-request-method": "GET",
        })
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


def test_missing_and_duplicate_host_headers():
    app = FastAPI()

    @app.get("/ok")
    def ok():
        return {"ok": True}

    gate = LocalHostGate(app)

    async def call(headers):
        responses = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            responses.append(message)

        scope = {
            "type": "http", "method": "GET", "path": "/ok", "raw_path": b"/ok",
            "headers": headers, "query_string": b"", "root_path": "",
            "scheme": "http", "server": ("127.0.0.1", 8765),
            "client": ("127.0.0.1", 1234), "http_version": "1.1",
            "asgi": {"version": "3.0"},
        }
        await gate(scope, receive, send)
        return responses[0]["status"]

    assert asyncio.run(call([])) == 400
    assert asyncio.run(call([(b"host", b"localhost"), (b"host", b"evil.example")])) == 400


def test_oversized_numeric_port_is_rejected_without_exception():
    # A 5,000-digit decimal string triggers Python integer-conversion limits
    # if parsed without a length guard. This must fail closed instead.
    for host in ("localhost", "127.0.0.1", "[::1]"):
        assert valid_local_authority(f"{host}:{'9' * 5000}") is False
    assert valid_local_authority("localhost:000080") is False


def test_oversized_port_returns_http_400():
    with TestClient(create_app(), base_url="http://localhost:8765") as client:
        response = client.get("/api/v1/health", headers={"host": "localhost:" + "9" * 5000})
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers
