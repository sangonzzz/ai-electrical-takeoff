# From Agente 5 → Agente 1

## Request: backend dependencies

Please update `backend/pyproject.toml`:

1. Change `sqlalchemy>=2` to `sqlalchemy[asyncio]>=2` (or add explicit `greenlet`) — async SQLAlchemy fails to import without it.
2. Optionally add `ENGINE=fake` and `INLINE_JOBS=false` to `.env.example` (Agente 5 settings).

## Also please (when you can)

1. Root `pyproject.toml` `[tool.pytest.ini_options] testpaths`: add `backend/tests`.
2. `Makefile` `demo` target: call  
   `uv run python backend/scripts/demo_upload.py`  
   (script is ready under backend/).
3. Compose `worker` command: ensure `app.worker.WorkerSettings` resolves (package install via uv sync should be enough; if not, add `PYTHONPATH=backend` or `cd backend`).
4. CI: add Postgres service + `alembic upgrade` / pytest for backend when convenient.

## Ready for Agente 6

M2/M3 endpoints documented in a separate message to Agente 6 once tests are green.
