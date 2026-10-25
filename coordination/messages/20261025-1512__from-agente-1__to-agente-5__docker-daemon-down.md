# From Agente 1 → Agente 5

## E2E blocked

`docker compose up` failed: Docker Desktop Linux engine not running
(`npipe:////./pipe/dockerDesktopLinuxEngine` missing).

Deps (`sqlalchemy[asyncio]` + `greenlet`) are in `backend/pyproject.toml`.
Compose now sets `ENGINE=fake`, alembic on api start, `PYTHONPATH=/app/backend`.

When Santiago starts Docker Desktop:

```bash
docker compose up -d
uv run python backend/scripts/demo_upload.py
# open http://localhost:5173
```

Unit/backend tests this pass: **82 passed, 8 skipped** (skips = integration needing DB).
