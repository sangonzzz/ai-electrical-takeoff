"""Electrical viewport discovery and scale parsing (owned by Agente 2).

Principle: the sheet is divided into cells by long black frame lines. The
electrical plan lives in the cell that contains the bold title
``ELECTRICAL PLAN - PLAN N``. The drawable viewport is that cell's area
*above* the title band (so mechanical / finish plans next door are excluded).
"""

from __future__ import annotations

import logging
import math
import re
from collections import defaultdict

from takeoff_engine.config import DEFAULT_PT_PER_FT
from takeoff_engine.models import BBox
from takeoff_engine.types import PageContext, Segment, Word

logger = logging.getLogger(__name__)

# Title "ELECTRICAL PLAN - PLAN N" is Arial Bold ~24.9 pt on these sheets.
_TITLE_MIN_SIZE_PT = 18.0

# Frame lines that divide the sheet into plan cells are long (hundreds of pt).
_MIN_FRAME_LENGTH_PT = 400.0
# Axis-aligned: allow ~1.5 pt drift from perfect H/V (flattened curves / join noise).
_AXIS_TOL_PT = 1.5

# Only keep verticals that actually run through the drawing area above the title.
_MIN_VERT_ABOVE_TITLE_PT = 200.0

# Inset from the cell frame so the border stroke itself is outside the viewport.
_CELL_INSET_PT = 2.0

# Search window under the title for the SCALE: line.
_SCALE_MAX_DY_PT = 50.0
_SCALE_MAX_DX_PT = 40.0

# ``1/4" = 1'-0"`` / ``3/16" = 1'-0"`` / ``1" = 10'-0"`` etc.
_SCALE_RE = re.compile(
    r"""
    SCALE\s*:\s*
    (?P<draw_num>\d+(?:/\d+)?)\s*"?\s*
    =\s*
    (?P<real_ft>\d+(?:\.\d+)?)\s*'\s*-?\s*(?P<real_in>\d+(?:\.\d+)?)?\s*"?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _seg_len(seg: Segment) -> float:
    return math.hypot(seg.x1 - seg.x0, seg.y1 - seg.y0)


def _is_vertical(seg: Segment) -> bool:
    return abs(seg.x1 - seg.x0) <= _AXIS_TOL_PT and abs(seg.y1 - seg.y0) > _AXIS_TOL_PT


def _is_horizontal(seg: Segment) -> bool:
    return abs(seg.y1 - seg.y0) <= _AXIS_TOL_PT and abs(seg.x1 - seg.x0) > _AXIS_TOL_PT


def _cluster_positions(positions: list[float], tol: float = 3.0) -> list[float]:
    """Merge nearly-equal x or y positions (double-stroke frames)."""
    if not positions:
        return []
    ordered = sorted(positions)
    clusters: list[list[float]] = [[ordered[0]]]
    for p in ordered[1:]:
        if p - clusters[-1][-1] <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [sum(c) / len(c) for c in clusters]


# Broader plan titles when the Escondido ``ELECTRICAL PLAN - PLAN N`` is absent (R7).
_TITLE_FALLBACK_RE = re.compile(
    r"\b((?:ELECTRICAL|POWER|LIGHTING)\s+PLAN)\b",
    re.IGNORECASE,
)
# Soft title match (other cities): slightly smaller / not always bold.
_TITLE_FALLBACK_MIN_SIZE_PT = 14.0


def find_electrical_title(ctx: PageContext) -> tuple[BBox, str]:
    """Locate the electrical / power / lighting plan title span.

    Prefers bold ``ELECTRICAL PLAN`` ≥ 18 pt (Escondido). Falls back to any
    ``ELECTRICAL|POWER|LIGHTING PLAN`` span ≥ 14 pt (R7 generalization).
    Ignores ``ELECTRICAL NOTES`` and rotated spine labels.
    """
    best: Word | None = None
    best_text = ""
    best_rank = 99
    for span in ctx.spans:
        if abs(span.dir_deg) > 5.0:
            continue  # skip rotated spine labels
        text = " ".join(span.text.split())
        upper = text.upper()
        if "NOTES" in upper:
            continue
        rank: int | None = None
        # Rank 0: Escondido-style bold title (unchanged thresholds).
        if (
            span.is_bold
            and span.size >= _TITLE_MIN_SIZE_PT
            and "ELECTRICAL PLAN" in upper
        ):
            rank = 0
        elif (
            span.size >= _TITLE_FALLBACK_MIN_SIZE_PT
            and _TITLE_FALLBACK_RE.search(upper)
        ):
            # Prefer bold when several soft matches exist.
            rank = 1 if span.is_bold else 2
        if rank is None:
            continue
        if best is None or rank < best_rank or (
            rank == best_rank and span.size > best.size
        ):
            best = span
            best_text = text
            best_rank = rank

    if best is None:
        raise ValueError(
            f"page {ctx.page_index}: no ELECTRICAL/POWER/LIGHTING PLAN title found"
        )

    x0, y0, x1, y1 = best.bbox
    return BBox(x0=x0, y0=y0, x1=x1, y1=y1), best_text


def largest_drawing_region(ctx: PageContext) -> BBox:
    """Content bbox of black ink with a small pad — last-resort viewport (R7)."""
    xs: list[float] = []
    ys: list[float] = []
    for seg in ctx.black_segments:
        xs.extend([seg.x0, seg.x1])
        ys.extend([seg.y0, seg.y1])
    for fill in ctx.black_fills:
        xs.extend([fill.x0, fill.x1])
        ys.extend([fill.y0, fill.y1])
    if not xs:
        return BBox(x0=0.0, y0=0.0, x1=ctx.page_width, y1=ctx.page_height)
    pad = 20.0
    return BBox(
        x0=max(0.0, min(xs) - pad),
        y0=max(0.0, min(ys) - pad),
        x1=min(ctx.page_width, max(xs) + pad),
        y1=min(ctx.page_height, max(ys) + pad),
    )


def _frame_verticals_above(
    segments: list[Segment], title_y0: float
) -> list[tuple[float, float]]:
    """Return (x, length_above_title) for long verticals that enter the drawing."""
    by_x: dict[int, float] = defaultdict(float)
    for seg in segments:
        if not _is_vertical(seg):
            continue
        y_lo, y_hi = min(seg.y0, seg.y1), max(seg.y0, seg.y1)
        # Portion of the segment that sits strictly above the title band.
        above_lo = y_lo
        above_hi = min(y_hi, title_y0)
        length_above = above_hi - above_lo
        if length_above < _MIN_VERT_ABOVE_TITLE_PT:
            continue
        x = round((seg.x0 + seg.x1) / 2.0)
        by_x[x] += length_above

    # Keep only positions whose total above-title length looks like a cell edge.
    strong = [(float(x), length) for x, length in by_x.items() if length >= _MIN_VERT_ABOVE_TITLE_PT]
    # Cluster double strokes, keep the longest member's x as representative.
    if not strong:
        return []
    strong.sort()
    clustered: list[tuple[float, float]] = []
    group_x = [strong[0][0]]
    group_len = [strong[0][1]]
    for x, length in strong[1:]:
        if x - group_x[-1] <= 3.0:
            group_x.append(x)
            group_len.append(length)
        else:
            # Pick the x with the most length in the group.
            i = max(range(len(group_len)), key=lambda k: group_len[k])
            clustered.append((group_x[i], sum(group_len)))
            group_x = [x]
            group_len = [length]
    i = max(range(len(group_len)), key=lambda k: group_len[k])
    clustered.append((group_x[i], sum(group_len)))
    return clustered


def _frame_horizontals(
    segments: list[Segment], x0: float, x1: float
) -> list[float]:
    """Y positions of long horizontals that overlap the cell's x-range."""
    by_y: dict[int, float] = defaultdict(float)
    span = max(1.0, x1 - x0)
    for seg in segments:
        if not _is_horizontal(seg):
            continue
        sx0, sx1 = min(seg.x0, seg.x1), max(seg.x0, seg.x1)
        overlap = min(sx1, x1) - max(sx0, x0)
        if overlap < 0.4 * span:
            continue
        length = _seg_len(seg)
        if length < _MIN_FRAME_LENGTH_PT:
            continue
        y = round((seg.y0 + seg.y1) / 2.0)
        by_y[y] += length
    ys = [float(y) for y, length in by_y.items() if length >= _MIN_FRAME_LENGTH_PT]
    return _cluster_positions(ys, tol=3.0)


def find_electrical_viewport(
    ctx: PageContext,
    warnings: list[str] | None = None,
) -> tuple[BBox, str]:
    """Locate the electrical plan drawing cell and its title string.

    Returns (viewport_bbox, title) where title is like
    ``ELECTRICAL PLAN - PLAN 1``. Must exclude mechanical and finish plans.

    Algorithm:
    1. Find the bold title span (ELECTRICAL / POWER / LIGHTING PLAN).
    2. Collect long vertical frame lines that extend *above* the title (lines
       that only exist below the title, e.g. a divider starting under a wide
       cell, are ignored — Plan 4 needs this).
    3. Cell left/right = nearest such verticals on either side of the title.
    4. Cell top = nearest long horizontal above the title that spans the cell,
       else a small page margin.
    5. Viewport bottom = title top (drawing sits above the title band).

    R7 generalization: if no title / cell frame is found, fall back to the
    largest black-ink drawing region and append a warning (do not raise).
    """
    try:
        title_bbox, title = find_electrical_title(ctx)
    except ValueError as exc:
        msg = f"viewport title fallback: {exc}; using largest drawing region"
        logger.warning("page %s: %s", ctx.page_index, msg)
        if warnings is not None:
            warnings.append(msg)
        return largest_drawing_region(ctx), "VIEWPORT_FALLBACK"

    title_y0 = title_bbox.y0
    title_cx = 0.5 * (title_bbox.x0 + title_bbox.x1)

    # Prefer black frame strokes; gray walls are architecture, not sheet cells.
    verticals = _frame_verticals_above(ctx.black_segments, title_y0)
    if len(verticals) < 2:
        # Rare fallback: include gray too (some sheets stroke frames in gray).
        verticals = _frame_verticals_above(
            ctx.black_segments + ctx.gray_segments, title_y0
        )

    left_candidates = [x for x, _ in verticals if x < title_bbox.x0 + 5.0]
    right_candidates = [x for x, _ in verticals if x > title_bbox.x1 - 5.0]
    if not left_candidates or not right_candidates:
        msg = (
            f"viewport frame fallback: no cell around title {title!r}; "
            "using largest drawing region"
        )
        logger.warning("page %s: %s", ctx.page_index, msg)
        if warnings is not None:
            warnings.append(msg)
        return largest_drawing_region(ctx), title

    cell_x0 = max(left_candidates)
    cell_x1 = min(right_candidates)
    if cell_x1 - cell_x0 < 50.0:
        msg = (
            f"viewport frame fallback: degenerate cell around title {title!r}; "
            "using largest drawing region"
        )
        logger.warning("page %s: %s", ctx.page_index, msg)
        if warnings is not None:
            warnings.append(msg)
        return largest_drawing_region(ctx), title

    horizontals = _frame_horizontals(ctx.black_segments, cell_x0, cell_x1)
    above = [y for y in horizontals if y < title_y0 - 2.0]
    cell_y0 = max(above) if above else 20.0

    # Drawing area is strictly above the title band.
    cell_y1 = title_y0

    inset = _CELL_INSET_PT
    viewport = BBox(
        x0=cell_x0 + inset,
        y0=cell_y0 + inset,
        x1=cell_x1 - inset,
        y1=cell_y1 - inset,
    )

    # Sanity: title center x must lie inside the viewport x-range.
    if not (viewport.x0 <= title_cx <= viewport.x1):
        logger.warning(
            "page %s: title center x=%.1f outside viewport x=[%.1f, %.1f]",
            ctx.page_index,
            title_cx,
            viewport.x0,
            viewport.x1,
        )

    return viewport, title


def _parse_fraction(token: str) -> float:
    """Parse ``1/4`` or ``0.25`` into a float."""
    token = token.strip()
    if "/" in token:
        num_s, den_s = token.split("/", 1)
        return float(num_s) / float(den_s)
    return float(token)


def scale_text_to_pt_per_ft(text: str) -> float | None:
    """Convert a ``SCALE: ...`` string into PDF points per foot, or None."""
    m = _SCALE_RE.search(text)
    if not m:
        return None
    draw_in = _parse_fraction(m.group("draw_num"))  # inches on paper
    real_ft = float(m.group("real_ft"))
    real_in = float(m.group("real_in") or 0.0)
    real_feet = real_ft + real_in / 12.0
    if real_feet <= 0.0 or draw_in <= 0.0:
        return None
    # inches_on_paper / feet_in_reality * 72 pt/inch
    return (draw_in / real_feet) * 72.0


def parse_scale(ctx: PageContext, title_bbox: BBox) -> float:
    """Parse ``SCALE: 1/4" = 1'-0"`` under the title into pt per foot.

    Fallback is config.DEFAULT_PT_PER_FT (18.0). Callers should warn when the
    fallback is used (pipeline does).
    """
    # Prefer full SCALE spans sitting just under the title, left-aligned with it.
    candidates: list[Word] = []
    for span in ctx.spans:
        if "SCALE" not in span.text.upper():
            continue
        if span.bbox[1] < title_bbox.y0 - 2.0:
            continue
        if span.bbox[1] > title_bbox.y1 + _SCALE_MAX_DY_PT:
            continue
        if abs(span.bbox[0] - title_bbox.x0) > _SCALE_MAX_DX_PT:
            continue
        candidates.append(span)

    for span in candidates:
        value = scale_text_to_pt_per_ft(span.text)
        if value is not None:
            return value

    # Fallback: any word token starting with SCALE near the title.
    for word in ctx.words:
        if not word.text.upper().startswith("SCALE"):
            continue
        if word.bbox[1] < title_bbox.y0 - 2.0:
            continue
        if word.bbox[1] > title_bbox.y1 + _SCALE_MAX_DY_PT:
            continue
        if abs(word.bbox[0] - title_bbox.x0) > _SCALE_MAX_DX_PT:
            continue
        # Reconstruct a short line of words at this y.
        cy = 0.5 * (word.bbox[1] + word.bbox[3])
        line = [
            w
            for w in ctx.words
            if abs(0.5 * (w.bbox[1] + w.bbox[3]) - cy) < 4.0
            and w.bbox[0] >= word.bbox[0] - 2.0
            and w.bbox[0] < word.bbox[0] + 220.0
        ]
        line.sort(key=lambda w: w.bbox[0])
        # Deduplicate identical tokens that share a span bbox.
        parts: list[str] = []
        seen: set[tuple[str, int]] = set()
        for w in line:
            key = (w.text, round(w.bbox[0]))
            if key in seen:
                continue
            seen.add(key)
            parts.append(w.text)
        value = scale_text_to_pt_per_ft(" ".join(parts))
        if value is not None:
            return value

    logger.warning(
        "page %s: SCALE under title not parsed; using default %.1f pt/ft",
        ctx.page_index,
        DEFAULT_PT_PER_FT,
    )
    return DEFAULT_PT_PER_FT
