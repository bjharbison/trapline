# Trapline V2 local API scaffold

This is **not a released V2 application**. The existing V1 single-file UI remains on `main` / `release/v1`. This backend has only a health endpoint; SQL, file ingestion and persistence belong to subsequent issues (#18–22).

## Quick start (Python 3.12+)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -e '.[test]'
python -m trapline_api
# in another terminal: curl http://127.0.0.1:8765/api/v1/health
```

Run tests: `python -m pytest -q` from `backend/`.

The server binds to `127.0.0.1:8765` by default; `TRAPLINE_HOST` accepts only numeric loopback addresses and `TRAPLINE_PORT` can override the port. Remote access, proxying, authentication and TLS require separate design/security review. CORS permits only `http://localhost:<TRAPLINE_PORT>` and `http://127.0.0.1:<TRAPLINE_PORT>` (default port 8765), without credentials; the allowlist follows the validated port at startup. Other origins and non-GET preflights remain disallowed. CORS is **not authentication** or protection against non-browser clients. The Host gate is a separate DNS-rebinding safeguard, and no mutation routes should be exposed without a CSRF/authentication review.

No uploads, database, cloud inference, analytics collection, or external HTTP requests are implemented. Never expose this unauthenticated API on a public interface. Future storage and document handling must follow `docs/ROADMAP_V2.md` and `docs/AGENT_DELIVERY_PLAYBOOK.md`.
