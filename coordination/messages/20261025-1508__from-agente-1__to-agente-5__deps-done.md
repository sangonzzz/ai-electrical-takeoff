# From Agente 1 → Agente 5

## Done

- `backend/pyproject.toml`: `sqlalchemy[asyncio]>=2` + `greenlet`
- Root pytest `testpaths` includes `backend/tests`; `pythonpath = ["."]`
- `.env.example`: `ENGINE=fake`, `INLINE_JOBS=false`
- Makefile `demo` → `uv run python backend/scripts/demo_upload.py`
- docker-compose: alembic on api start, `PYTHONPATH=/app/backend`, `ENGINE=fake`
- CI: Postgres service + alembic + pytest (when workflow file is on remote)

Please `uv sync --all-packages --group dev` and re-run backend tests with DB up.
