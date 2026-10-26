"""Stable content ids for LLM prompts so disk cache survives fresh UUIDs.

Agente 2 assigns ``uuid4`` to each ``LegendEntry`` / detection per run. If we
send those UUIDs in the prompt, ``.cache/llm`` never hits on a second analyze.
We map content → stable id for the model, then map answers back to the live
object ids. Geometry / detection rules are unchanged.
"""

from __future__ import annotations

import hashlib


def stable_legend_id(
    description: str,
    codes: list[str],
    bbox: tuple[float, float, float, float],
) -> str:
    """Deterministic id from legend row content + glyph box (rounded)."""
    x0, y0, x1, y1 = (round(v, 2) for v in bbox)
    payload = "|".join(
        [
            description.strip(),
            ",".join(codes),
            f"{x0},{y0},{x1},{y1}",
        ]
    )
    return "L" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def stable_candidate_id(
    page_index: int,
    bbox: tuple[float, float, float, float],
) -> str:
    """Deterministic id from page + candidate bbox (rounded)."""
    x0, y0, x1, y1 = (round(v, 2) for v in bbox)
    payload = f"{page_index}|{x0},{y0},{x1},{y1}"
    return "C" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
