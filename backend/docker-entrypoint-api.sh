#!/bin/sh
# API-only entrypoint: ensure DATABASE_URL DB exists, migrate, then exec.
# Worker overrides entrypoint and does not run alembic.
set -e
cd /app/backend
python -c "import asyncio; from app.settings import get_settings; from app.db_bootstrap import ensure_database; asyncio.run(ensure_database(get_settings().database_url))"
alembic upgrade head
cd /app
exec "$@"
