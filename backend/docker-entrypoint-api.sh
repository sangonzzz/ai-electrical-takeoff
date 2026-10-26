#!/bin/sh
# API-only entrypoint: migrate then exec the main process.
# Worker overrides entrypoint and does not run alembic.
set -e
cd /app/backend
alembic upgrade head
cd /app
exec "$@"
