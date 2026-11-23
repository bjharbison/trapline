"""Versioned API scaffold. No uploads, database, cloud calls or credentials yet."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import __version__
from .config import Settings
from .host_gate import LocalHostGate


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def create_app(settings: Settings | None = None) -> FastAPI:
    # Keep trusted browser origins aligned with the validated runtime port.
    configured_port = (settings if settings is not None else Settings.from_env()).port
    app = FastAPI(
        title="Trapline local API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # A separate local UI may use these explicit origins. No wildcard CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://127.0.0.1:{configured_port}",
            f"http://localhost:{configured_port}",
        ],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    # Reject hostile Host headers before CORS preflight or route handlers.
    app.add_middleware(LocalHostGate)

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="trapline-api", version=__version__)

    return app


app = create_app()
