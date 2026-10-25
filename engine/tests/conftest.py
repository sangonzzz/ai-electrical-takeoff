"""Shared pytest fixtures for the engine."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANS_PDF = REPO_ROOT / "data" / "plans" / "escondido_plans.pdf"


@pytest.fixture(scope="session")
def plans_pdf() -> Path:
    assert PLANS_PDF.is_file(), f"Missing plans PDF at {PLANS_PDF}"
    return PLANS_PDF
