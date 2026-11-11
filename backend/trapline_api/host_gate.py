"""Reject hostile Host authorities before local API routes or CORS run.

The allowlist is independent of CORS, which cannot prevent DNS rebinding.
"""

from ipaddress import ip_address
from starlette.responses import PlainTextResponse


def valid_local_authority(authority: str) -> bool:
    """Accept localhost or numeric loopback IPv4/IPv6 with optional TCP port."""
    if not authority or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in authority):
        return False
    if authority.startswith("["):
        end = authority.find("]")
        if end == -1:
            return False
        host = authority[1:end]
        suffix = authority[end + 1:]
        try:
            address = ip_address(host)
        except ValueError:
            return False
        if address.version != 6 or str(address) != "::1":
            return False
    else:
        if authority.count(":") > 1:
            return False
        host, sep, port = authority.partition(":")
        suffix = f":{port}" if sep else ""
        if host != "localhost":
            try:
                if not ip_address(host).is_loopback:
                    return False
            except ValueError:
                return False
    if not suffix:
        return True
    if not suffix.startswith(":"):
        return False
    port = suffix[1:]
    return port.isascii() and port.isdecimal() and 1 <= int(port) <= 65535


class LocalHostGate:
    """ASGI middleware: reject missing, duplicate or non-loopback Host headers."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        hosts = [value for key, value in scope.get("headers", []) if key.lower() == b"host"]
        if len(hosts) != 1:
            await PlainTextResponse("Invalid Host", status_code=400)(scope, receive, send)
            return
        try:
            authority = hosts[0].decode("ascii")
        except UnicodeDecodeError:
            await PlainTextResponse("Invalid Host", status_code=400)(scope, receive, send)
            return
        if not valid_local_authority(authority):
            await PlainTextResponse("Invalid Host", status_code=400)(scope, receive, send)
            return
        await self.app(scope, receive, send)
