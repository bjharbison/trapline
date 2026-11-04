"""Strict local-only runtime configuration for the first V2 backend milestone."""

from dataclasses import dataclass
from ipaddress import ip_address
import os


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8765

    def __post_init__(self) -> None:
        try:
            address = ip_address(self.host)
        except ValueError as exc:
            raise ValueError("TRAPLINE_HOST must be a numeric loopback IP address") from exc
        if not address.is_loopback:
            raise ValueError("Trapline V2 must bind to loopback; remote access needs a security review")
        if not 1 <= self.port <= 65535:
            raise ValueError("TRAPLINE_PORT must be between 1 and 65535")

    @classmethod
    def from_env(cls) -> "Settings":
        raw_port = os.getenv("TRAPLINE_PORT", "8765")
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ValueError("TRAPLINE_PORT must be an integer") from exc
        return cls(host=os.getenv("TRAPLINE_HOST", "127.0.0.1"), port=port)
