"""Pytest fixtures: AsyncClient against a dedicated Postgres test DB."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force test settings before app import
REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DB = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://takeoff:takeoff@localhost:5432/takeoff_test",
)
os.environ["DATABASE_URL"] = TEST_DB
os.environ["ENGINE"] = "fake"
os.environ["INLINE_JOBS"] = "true"
os.environ["ENABLE_BOM"] = "true"
# Tests use metadata.create_all; skip lifespan alembic.
os.environ["AUTO_MIGRATE"] = "false"

from app.db import Base  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import (  # noqa: E402, F401 — register tables
    AnalysisRun,
    BoxRow,
    Correction,
    DetectionRow,
    Document,
    LegendEntryRow,
    RoomRow,
    Sheet,
    WireRunRow,
)
from app.settings import get_settings  # noqa: E402

get_settings.cache_clear()


async def _ensure_test_database() -> None:
    """Create takeoff_test if missing (connects to the default takeoff DB)."""
    admin_url = TEST_DB.rsplit("/", 1)[0] + "/takeoff"
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    db_name = TEST_DB.rsplit("/", 1)[-1]
    async with engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"),
            {"n": db_name},
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def prepared_db() -> AsyncIterator[None]:
    try:
        await _ensure_test_database()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres not available for backend tests: {exc}")

    engine = create_async_engine(TEST_DB, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Cannot prepare test DB: {exc}")

    # Point the app engine at the test DB (recreate module engine bindings)
    import app.db as db_mod

    await db_mod.engine.dispose()
    db_mod.engine = engine
    db_mod.SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    get_settings.cache_clear()
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client(prepared_db: None) -> AsyncIterator[AsyncClient]:
    # Truncate between tests
    import app.db as db_mod

    async with db_mod.engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_pdf() -> Path:
    path = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"
    if not path.exists():
        pytest.skip("escondido_plans.pdf missing")
    return path
