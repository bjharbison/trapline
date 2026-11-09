# V2 SQL persistence foundation (issue #18, first increment)

This PR introduces a **schema only**. It does not expose a database endpoint, save uploaded files, or enable autosave. Browser-only V1 and the existing FastAPI health API remain unchanged.

From `backend/`, with Python 3.12+ and `pip install -e '.[test]'`:

```bash
export TRAPLINE_DATA_DIR="$HOME/.local/share/trapline" # optional; default is this path
python -m alembic -c alembic.ini upgrade head
python -m pytest -q
```

`TRAPLINE_DATABASE_URL` can explicitly select a SQLite URL for tests and later deployments. Default is `~/.local/share/trapline/trapline.db`, outside the Git checkout. Parent directory is created with owner-only permissions where supported. Do not put a database or real source documents in the public repository. Back up before upgrades and store backups separately. `downgrade` is destructive and is for disposable test databases only; never use it on user data.

Initial tables: `investigations`, `documents`, `entities`, `relationships`, `evidence`. Foreign keys are enabled for each SQLite connection and delete behavior is restrictive. Document records contain metadata and extracted text; original binary file storage is issue #19. Entity cross-investigation reference enforcement, rich evidence offsets, analyst edit history, blob integrity, schema validation, backup/restore, API authorization and CRUD endpoints remain future work. Do not expose state-changing routes before security issue #34 and Origin/CSRF review.

Validation: `tests/test_database.py` uses synthetic names, tests migration idempotency, persistence across engine restart, relationship evidence, and rejection of orphan records. CI runs these through the existing backend pytest workflow.
