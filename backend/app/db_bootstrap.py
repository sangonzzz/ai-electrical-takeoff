"""Ensure DATABASE_URL database exists and apply Alembic migrations.

Used on API startup so e2e (or any env) can point at a separate Postgres DB
via DATABASE_URL and get a migrated schema without manual steps.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)

_DB_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def split_database_url(database_url: str) -> tuple[str, str]:
    """Return (admin_url_to_postgres_db, target_db_name)."""
    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/").split("?")[0]
    if not db_name or not _DB_NAME_RE.fullmatch(db_name):
        raise ValueError(f"unsafe or empty database name in DATABASE_URL: {db_name!r}")
    admin_url = urlunparse(parsed._replace(path="/postgres"))
    return admin_url, db_name


async def ensure_database(database_url: str) -> None:
    """CREATE DATABASE if the name in DATABASE_URL does not exist yet."""
    admin_url, db_name = split_database_url(database_url)
    # Prefer /postgres; fall back to /takeoff (compose default POSTGRES_DB).
    candidates = [admin_url]
    takeoff_admin = urlunparse(urlparse(admin_url)._replace(path="/takeoff"))
    if takeoff_admin != admin_url:
        candidates.append(takeoff_admin)

    last_exc: Exception | None = None
    for url in candidates:
        engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
        try:
            async with engine.connect() as conn:
                exists = await conn.scalar(
                    text("SELECT 1 FROM pg_database WHERE datname = :n"),
                    {"n": db_name},
                )
                if not exists:
                    logger.info("Creating database %s (from DATABASE_URL)", db_name)
                    await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                else:
                    logger.debug("Database %s already exists", db_name)
            return
        except Exception as exc:  # noqa: BLE001 — try next admin DB
            last_exc = exc
            logger.debug("Admin connect via %s failed: %s", url.rsplit("/", 1)[-1], exc)
        finally:
            await engine.dispose()
    assert last_exc is not None
    raise last_exc


def run_alembic_upgrade() -> None:
    """Run `alembic upgrade head` against get_settings().database_url."""
    from alembic import command
    from alembic.config import Config

    from app.settings import get_settings

    get_settings.cache_clear()
    url = get_settings().database_url
    ini = _BACKEND_ROOT / "alembic.ini"
    cfg = Config(str(ini))
    # env.py also overwrites sqlalchemy.url from settings; set for clarity.
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    logger.info("Alembic upgrade head OK → %s", url.rsplit("/", 1)[-1])


async def bootstrap_database(database_url: str) -> None:
    """Create DB if needed, then migrate schema to head."""
    await ensure_database(database_url)
    run_alembic_upgrade()
