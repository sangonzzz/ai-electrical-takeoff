"""Unit tests for DATABASE_URL parsing / bootstrap helpers (no Postgres needed)."""

from __future__ import annotations

import pytest

from app.db_bootstrap import split_database_url


def test_split_database_url_e2e_name() -> None:
    admin, name = split_database_url(
        "postgresql+asyncpg://takeoff:takeoff@db:5432/takeoff_e2e"
    )
    assert name == "takeoff_e2e"
    assert admin.endswith("/postgres")
    assert "takeoff:takeoff@db:5432" in admin


def test_split_rejects_unsafe_name() -> None:
    with pytest.raises(ValueError):
        split_database_url("postgresql+asyncpg://u:p@localhost:5432/evil;drop")
