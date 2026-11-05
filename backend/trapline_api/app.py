"""Versioned API scaffold. No uploads, database, cloud calls or credentials yet."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ipaddress import ip_address
from urllib.parse import urlsplit

from starlette.responses import PlainTextResponse
from pydantic import BaseModel

from . import __version__


class LoopbackHostMiddleware:
    """Reject Host values outside explicit local names, including IPv6 loopback."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        hosts = [value for key, value in scope.get("headers", []) if key.lower() == b"host"]
        valid = False
        if len(hosts) == 1:
            try:
                raw = hosts[0].decode("ascii")
                # urlsplit handles bracketed IPv6 and optional port unambiguously.
                parsed = urlsplit("//" + raw)
                name = parsed.hostname
                port = parsed.port
                valid = (
                    name is not None
                    and parsed.username is None
                    and parsed.password is None
                    and parsed.path == ""
                    and parsed.query == ""
                    and parsed.fragment == ""
                    and (port is None or 1 <= port <= 65535)
                    and (
                        name.lower() == "localhost"
                        or (ip_address(name).is_loopback if name != "localhost" else True)
                    )
                )
            except (UnicodeDecodeError, ValueError):
                pass
        if not valid:
            await PlainTextResponse("Invalid host header", status_code=400)(scope, receive, send)
            return
        await self.app(scope, receive, send)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trapline local API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # Block forged Host headers (including DNS-rebinding-style hostnames).
    # This is defense-in-depth, not authentication or CSRF protection.
    app.add_middleware(LoopbackHostMiddleware)
    # A separate local UI may use these explicit origins. No wildcard CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:8765",
            "http://localhost:8765",
        ],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="trapline-api", version=__version__)

    return app


app = create_app()
