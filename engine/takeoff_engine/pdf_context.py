"""Load a PDF page into styled vector primitives and text words.

PyMuPDF gotcha (SPEC section 1): axis-aligned lines have a zero-area ``rect``,
so ``rect.intersects(clip)`` silently drops them. We never filter with raw
rects; callers that need a clip must inflate or test endpoints.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pymupdf

from takeoff_engine.types import FillPath, PageContext, Segment, Word

# Style thresholds matching the Escondido plans (SPEC section 1).
_BLACK = 0.0
_GRAY_STROKE = 0.67
_GRAY_FILL = 0.75
_COLOR_EPS = 0.05

# Sample Bezier curves into short straight segments (~2 pt median on these plans).
_CURVE_SAMPLES = 8


def _is_near(value: float, target: float, eps: float = _COLOR_EPS) -> bool:
    return abs(value - target) <= eps


def _rgb_channel(color: Any) -> float | None:
    """Return the first RGB channel, or None if color is missing/transparent."""
    if color is None:
        return None
    if isinstance(color, (int, float)):
        return float(color)
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return float(color[0])
    return None


def _is_black(color: Any) -> bool:
    ch = _rgb_channel(color)
    return ch is not None and _is_near(ch, _BLACK)


def _is_gray_stroke(color: Any) -> bool:
    ch = _rgb_channel(color)
    return ch is not None and _is_near(ch, _GRAY_STROKE)


def _is_gray_fill(color: Any) -> bool:
    ch = _rgb_channel(color)
    return ch is not None and _is_near(ch, _GRAY_FILL)


def _bezier_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    u = 1.0 - t
    x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def _flatten_items(items: list[Any]) -> list[tuple[float, float, float, float]]:
    """Flatten drawing items (l, re, qu, c) into straight segments.

    Returns a list of (x0, y0, x1, y1) in page coordinates.
    """
    segments: list[tuple[float, float, float, float]] = []
    for item in items:
        if not item:
            continue
        kind = item[0]
        if kind == "l":
            # ("l", p1, p2) — each point is a Point-like with .x/.y or a pair
            p1, p2 = item[1], item[2]
            segments.append((_pt_x(p1), _pt_y(p1), _pt_x(p2), _pt_y(p2)))
        elif kind == "re":
            # ("re", rect, orientation) — emit four edges of the rectangle
            rect = item[1]
            x0, y0, x1, y1 = float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)
            segments.extend(
                [
                    (x0, y0, x1, y0),
                    (x1, y0, x1, y1),
                    (x1, y1, x0, y1),
                    (x0, y1, x0, y0),
                ]
            )
        elif kind == "qu":
            # ("qu", quad) — four corners; emit four edges
            quad = item[1]
            pts = [_as_xy(p) for p in (quad.ul, quad.ur, quad.lr, quad.ll)]
            for i in range(4):
                a, b = pts[i], pts[(i + 1) % 4]
                segments.append((a[0], a[1], b[0], b[1]))
        elif kind == "c":
            # ("c", p1, p2, p3, p4) cubic Bezier — sample into short segments
            p0 = _as_xy(item[1])
            p1 = _as_xy(item[2])
            p2 = _as_xy(item[3])
            p3 = _as_xy(item[4])
            prev = p0
            for i in range(1, _CURVE_SAMPLES + 1):
                t = i / _CURVE_SAMPLES
                cur = _bezier_point(p0, p1, p2, p3, t)
                segments.append((prev[0], prev[1], cur[0], cur[1]))
                prev = cur
    return segments


def _pt_x(p: Any) -> float:
    return float(p.x) if hasattr(p, "x") else float(p[0])


def _pt_y(p: Any) -> float:
    return float(p.y) if hasattr(p, "y") else float(p[1])


def _as_xy(p: Any) -> tuple[float, float]:
    return (_pt_x(p), _pt_y(p))


def _fill_from_items(items: list[Any], color: Any) -> FillPath | None:
    """Build a FillPath bbox from drawing items (and keep polygon points)."""
    points: list[tuple[float, float]] = []
    for item in items:
        if not item:
            continue
        kind = item[0]
        if kind == "l":
            points.append(_as_xy(item[1]))
            points.append(_as_xy(item[2]))
        elif kind == "re":
            rect = item[1]
            points.extend(
                [
                    (float(rect.x0), float(rect.y0)),
                    (float(rect.x1), float(rect.y0)),
                    (float(rect.x1), float(rect.y1)),
                    (float(rect.x0), float(rect.y1)),
                ]
            )
        elif kind == "qu":
            quad = item[1]
            points.extend([_as_xy(p) for p in (quad.ul, quad.ur, quad.lr, quad.ll)])
        elif kind == "c":
            for i in range(1, 5):
                points.append(_as_xy(item[i]))
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    rgb = None
    ch = _rgb_channel(color)
    if ch is not None and isinstance(color, (list, tuple)) and len(color) >= 3:
        rgb = (float(color[0]), float(color[1]), float(color[2]))
    elif ch is not None:
        rgb = (ch, ch, ch)
    return FillPath(
        x0=min(xs),
        y0=min(ys),
        x1=max(xs),
        y1=max(ys),
        color=rgb,
        points=tuple(points),
    )


def _dir_to_deg(direction: Any) -> float:
    """Convert PyMuPDF line dir (cos, sin) to degrees, 0 = rightward."""
    if direction is None:
        return 0.0
    if isinstance(direction, (list, tuple)) and len(direction) >= 2:
        dx, dy = float(direction[0]), float(direction[1])
        if dx == 0.0 and dy == 0.0:
            return 0.0
        return math.degrees(math.atan2(dy, dx))
    return 0.0


def _font_is_bold(font: str) -> bool:
    lower = font.lower()
    return "bold" in lower or lower.endswith("-bd") or "black" in lower


def _extract_words_and_spans(page: pymupdf.Page) -> tuple[list[Word], list[Word]]:
    """Extract words and spans with font, size, bold, and line direction."""
    words: list[Word] = []
    spans: list[Word] = []
    data = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)
    for block in data.get("blocks", []):
        if block.get("type", 0) != 0:
            continue
        for line in block.get("lines", []):
            dir_deg = _dir_to_deg(line.get("dir"))
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text:
                    continue
                bbox = span.get("bbox", (0, 0, 0, 0))
                font = span.get("font", "")
                size = float(span.get("size", 0.0))
                is_bold = _font_is_bold(font)
                span_word = Word(
                    text=text,
                    bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
                    font=font,
                    size=size,
                    dir_deg=dir_deg,
                    is_bold=is_bold,
                )
                spans.append(span_word)
                # Split span into whitespace-separated words, sharing geometry.
                # Exact per-word bboxes would need get_text("words"); for room
                # labels multi-word spans are joined later by Agente 3.
                for token in text.split():
                    if not token:
                        continue
                    words.append(
                        Word(
                            text=token,
                            bbox=span_word.bbox,
                            font=font,
                            size=size,
                            dir_deg=dir_deg,
                            is_bold=is_bold,
                        )
                    )
    return words, spans


def load_page(pdf_path: str | Path, page_index: int) -> PageContext:
    """Load one PDF page into styled segments, fills, words and spans.

    Splits drawings by style:
    - black stroke (0,0,0) -> black_segments
    - black fill -> black_fills
    - gray stroke (~0.67) -> gray_segments
    - gray fill (~0.75) -> gray_fills

    Does **not** filter by clip rect (would drop zero-area axis-aligned lines).
    """
    path = str(pdf_path)
    doc = pymupdf.open(path)
    try:
        if page_index < 0 or page_index >= len(doc):
            raise IndexError(f"page_index {page_index} out of range (0..{len(doc) - 1})")
        page = doc[page_index]
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)

        black_segments: list[Segment] = []
        black_fills: list[FillPath] = []
        gray_segments: list[Segment] = []
        gray_fills: list[FillPath] = []

        for drawing in page.get_drawings():
            stroke = drawing.get("color")
            fill = drawing.get("fill")
            width = float(drawing.get("width") or 0.0)
            items = drawing.get("items") or []

            # Stroke primitives
            if stroke is not None and width > 0:
                segs = _flatten_items(items)
                rgb = None
                ch = _rgb_channel(stroke)
                if ch is not None and isinstance(stroke, (list, tuple)) and len(stroke) >= 3:
                    rgb = (float(stroke[0]), float(stroke[1]), float(stroke[2]))
                elif ch is not None:
                    rgb = (ch, ch, ch)
                target: list[Segment] | None = None
                if _is_black(stroke):
                    target = black_segments
                elif _is_gray_stroke(stroke):
                    target = gray_segments
                if target is not None:
                    for x0, y0, x1, y1 in segs:
                        target.append(
                            Segment(x0=x0, y0=y0, x1=x1, y1=y1, width=width, color=rgb)
                        )

            # Fill primitives
            if fill is not None:
                fp = _fill_from_items(items, fill)
                if fp is not None:
                    if _is_black(fill):
                        black_fills.append(fp)
                    elif _is_gray_fill(fill):
                        gray_fills.append(fp)

        words, spans = _extract_words_and_spans(page)

        return PageContext(
            page_index=page_index,
            page_width=page_width,
            page_height=page_height,
            black_segments=black_segments,
            black_fills=black_fills,
            gray_segments=gray_segments,
            gray_fills=gray_fills,
            words=words,
            spans=spans,
            pdf_path=path,
        )
    finally:
        doc.close()


def count_segments_in_box(
    segments: list[Segment],
    box: tuple[float, float, float, float],
    inflate: float = 0.5,
) -> int:
    """Count segments whose endpoints fall in an inflated axis-aligned box.

    Inflating avoids the zero-area rect intersect bug for axis-aligned lines.
    """
    x0, y0, x1, y1 = box
    x0 -= inflate
    y0 -= inflate
    x1 += inflate
    y1 += inflate

    def inside(x: float, y: float) -> bool:
        return x0 <= x <= x1 and y0 <= y <= y1

    n = 0
    for s in segments:
        if inside(s.x0, s.y0) or inside(s.x1, s.y1):
            n += 1
            continue
        # Also count if the segment crosses the box (midpoint heuristic + AABB).
        sx0, sx1 = min(s.x0, s.x1), max(s.x0, s.x1)
        sy0, sy1 = min(s.y0, s.y1), max(s.y0, s.y1)
        if sx0 <= x1 and sx1 >= x0 and sy0 <= y1 and sy1 >= y0:
            n += 1
    return n
