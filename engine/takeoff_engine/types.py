"""Internal shared dataclasses used across engine modules.

These are not part of the JSON contract; they carry vector primitives and
intermediate pipeline state between pdf_context, symbols, classify, and LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Segment:
    """Straight line segment in PDF points (page space, origin top-left)."""

    x0: float
    y0: float
    x1: float
    y1: float
    width: float = 0.0
    color: tuple[float, ...] | None = None


@dataclass(frozen=True, slots=True)
class FillPath:
    """Closed filled path approximated as a bounding rect plus optional points."""

    x0: float
    y0: float
    x1: float
    y1: float
    color: tuple[float, ...] | None = None
    points: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True, slots=True)
class Word:
    """A text word from the PDF text layer."""

    text: str
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1
    font: str
    size: float
    dir_deg: float  # rotation degrees from line "dir"
    is_bold: bool


@dataclass
class PageContext:
    """All vector and text primitives for one PDF page."""

    page_index: int
    page_width: float
    page_height: float
    black_segments: list[Segment]
    black_fills: list[FillPath]
    gray_segments: list[Segment]
    gray_fills: list[FillPath]
    words: list[Word]
    spans: list[Word]
    pdf_path: str


@dataclass
class Candidate:
    """A clustered symbol candidate before classification."""

    id: str
    bbox: tuple[float, float, float, float]
    center: tuple[float, float]
    segment_ids: list[int]
    fill_ids: list[int]
    features: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Adjudication:
    """LLM adjudication result for one ambiguous candidate."""

    candidate_id: str
    label: str
    confidence: float
    reason: str
