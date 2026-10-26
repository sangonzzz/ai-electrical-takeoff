# Backend + engine image. Build context = repo root:
#   docker build -f backend/Dockerfile .
# Venv lives at /opt/venv inside the image — never bind-mounted onto the host.

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/backend \
    PYTHONDONTWRITEBYTECODE=1

# 1) Lock + package manifests (layer cache for deps)
COPY pyproject.toml uv.lock ./
COPY engine/pyproject.toml engine/pyproject.toml
COPY backend/pyproject.toml backend/pyproject.toml

# Minimal package trees so workspace members can be built/installed
COPY engine/takeoff_engine engine/takeoff_engine
COPY backend/app backend/app
COPY backend/alembic.ini backend/alembic.ini
COPY backend/alembic backend/alembic

RUN uv sync --frozen --all-packages --no-dev

# 2) Runtime data (prices, assumptions, fixtures for FakeEngine if ever used)
COPY data data
COPY contracts contracts
COPY backend/scripts backend/scripts

COPY backend/docker-entrypoint-api.sh /docker-entrypoint-api.sh
RUN chmod +x /docker-entrypoint-api.sh \
    && mkdir -p /app/storage /app/.cache

WORKDIR /app

# Default = API; compose overrides for worker
ENTRYPOINT ["/docker-entrypoint-api.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
