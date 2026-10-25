"""Claude LLM tasks for legend interpretation and adjudication (owned by Agente 4)."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.models import LegendEntry
from takeoff_engine.types import Adjudication, Candidate


def interpret_legend(entries: list[LegendEntry], legend_png: bytes) -> list[LegendEntry]:
    """Map legend rows to category/subtype and code meanings via Claude.

    Unknown is allowed. Enums must validate against the contracts.
    """
    raise NotImplementedError("Agente 4: implement interpret_legend")


def adjudicate(
    pdf_path: str | Path,
    page_index: int,
    candidates: list[Candidate],
    legend: list[LegendEntry],
) -> list[Adjudication]:
    """Ask Claude to label ambiguous candidates from the allowed list.

    Never returns coordinates — only label, confidence, and reason.
    """
    raise NotImplementedError("Agente 4: implement adjudicate")


def baseline_vision_takeoff(
    sheet_png: bytes,
    room_names: list[str],
) -> dict[str, dict[str, int]]:
    """LLM-only takeoff baseline for eval comparison (room -> counts)."""
    raise NotImplementedError("Agente 4: implement baseline_vision_takeoff")
