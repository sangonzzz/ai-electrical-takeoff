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
from sqlalchemy.pool import NullPool

# Force test settings before app import
REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DB = os.environ.get(
    "TEST_DATABASE_URL",
    # Isolated test Postgres (never the demo `takeoff` DB). Default port 55432
    # matches a dedicated container; override via TEST_DATABASE_URL as needed.
    "postgresql+asyncpg://takeoff:takeoff@127.0.0.1:55432/takeoff_test",
)
os.environ["DATABASE_URL"] = TEST_DB
os.environ["ENGINE"] = "fake"
os.environ["INLINE_JOBS"] = "true"
os.environ["ENABLE_BOM"] = "true"
os.environ["AUTO_MIGRATE"] = "false"

from app.db import Base  # noqa: E402
import app.db as db_mod  # noqa: E402
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

_import_engine = db_mod.engine
db_mod.engine = create_async_engine(TEST_DB, poolclass=NullPool)
db_mod.SessionLocal = async_sessionmaker(
    db_mod.engine, expire_on_commit=False, class_=AsyncSession
)
_import_engine.sync_engine.dispose()
get_settings.cache_clear()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def prepared_db() -> AsyncIterator[None]:
    try:
        from app.db_bootstrap import ensure_database

        await ensure_database(TEST_DB)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres not available for backend tests: {exc}")

    engine = create_async_engine(TEST_DB, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Cannot prepare test DB: {exc}")

    db_mod.engine = engine
    db_mod.SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    get_settings.cache_clear()
    yield
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def client(prepared_db: None) -> AsyncIterator[AsyncClient]:
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
