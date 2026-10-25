"""Legend template matching and code-token subtype refinement (owned by Agente 2)."""

from __future__ import annotations

from typing import Any

from takeoff_engine.models import Detection, LegendEntry
from takeoff_engine.types import Candidate, PageContext


def classify_candidates(
    ctx: PageContext,
    candidates: list[Candidate],
    legend: list[LegendEntry],
    templates: dict[str, Any],
    sheet_id: str,
) -> list[Detection]:
    """Match candidates to legend templates and attach nearby code tokens.

    Low-confidence or close top-two scores set ``needs_review=True``.
    """
    raise NotImplementedError("Agente 2: implement classify_candidates")
