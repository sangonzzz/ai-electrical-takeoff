"""Legend row extraction and template building (owned by Agente 2).

Principle: each legend row is ``symbol geometry (left) + codes + description
(right)``. Category/subtype come from rule-based keyword mapping on the
description (SPEC §1–2); Agente 4 may refine via ``interpret_legend``.
"""

from __future__ import annotations

import logging
import math
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from takeoff_engine.models import BBox, Category, LegendEntry
from takeoff_engine.types import FillPath, PageContext, Segment, Word

logger = logging.getLogger(__name__)

# --- geometry thresholds (why: interview-defensible) ---

# Bold LEGEND title is ~24.9 pt; body is ~9.6.
_LEGEND_TITLE_MIN_SIZE = 18.0

# Description text in the legend is Arial ~9.6 pt; codes are ~6.5.
_DESC_SIZE_MIN = 8.0
_DESC_SIZE_MAX = 12.0
_CODE_SIZE_MAX = 7.5

# Cluster primitives into one legend symbol when bbox gap < this (same as plan).
_SYMBOL_GAP_PT = 1.5

# Description lines of one multi-line row: vertical gap and x-align tolerance.
_DESC_LINE_GAP_PT = 12.0
_DESC_X_ALIGN_PT = 18.0

# Pair a symbol with description text sitting to its right within this band.
_PAIR_MAX_DX_PT = 80.0
_PAIR_Y_OVERLAP_MIN_PT = 2.0

# Code tokens must sit near the symbol (above / beside).
_CODE_RADIUS_PT = 28.0

# Drop frame rules and wiring dashes from symbol clusters.
_MAX_SYMBOL_WIDTH_PT = 130.0  # ceiling fan is ~116 pt — keep; attic panel is wider? ~46
_MAX_SYMBOL_HEIGHT_PT = 130.0
_MIN_SYMBOL_AREA_PT2 = 8.0
_LONG_SEG_PT = 40.0  # a single segment longer than this is a rule/underline, not a glyph


@dataclass
class LegendTemplate:
    """Vector primitives for one legend symbol, ready for raster matching."""

    entry_id: str
    # Symbol bbox in page coordinates.
    bbox: tuple[float, float, float, float]
    segments: list[Segment] = field(default_factory=list)
    fills: list[FillPath] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Rule-based description → (category, subtype, combined, exclude)
# ---------------------------------------------------------------------------

# Order matters: first match wins. More specific phrases before generic ones.
_RULES: list[tuple[re.Pattern[str], Category | None, str | None, bool, bool]] = [
    # (pattern, category, subtype, combined, exclude)
    (re.compile(r"ATTIC\s+ACCESS", re.I), None, None, False, True),
    (re.compile(r"COLD\s+WATER|HOT\s+WATER|HOSE\s+BIBB|SHUT\s+OF", re.I), None, None, False, True),
    (re.compile(r"\bCW\b|\bHW\b|\bHB\b|SOV", re.I), None, None, False, True),
    (re.compile(r"ELECTRICAL\s+WIRING|\bWIRING\b", re.I), None, None, False, True),
    (re.compile(r"CEILING\s+FAN", re.I), Category.CEILING_FAN, "ceiling_fan", False, False),
    (re.compile(r"INDOOR\s+AIR\s+QUALITY|\bIAQ\b", re.I), Category.EXHAUST_FAN, "indoor_air_quality", False, False),
    (re.compile(r"EXHAUST\s+FAN", re.I), Category.EXHAUST_FAN, "bath_exhaust", False, False),
    (re.compile(r"VAPOR\s+PROOF", re.I), Category.LIGHT, "recessed_vapor_proof", False, False),
    (re.compile(r"RECESSED.*DOWNLIGHT|DOWNLIGHT", re.I), Category.LIGHT, "recessed", False, False),
    (re.compile(r"PENDANT", re.I), Category.LIGHT, "pendant", False, False),
    (re.compile(r"EXTERIOR\s+WALL", re.I), Category.LIGHT, "exterior_wall", False, False),
    (re.compile(r"WALL\s+MOUNTED", re.I), Category.LIGHT, "wall", False, False),
    (re.compile(r"SMOKE\s*/\s*CARBON|SMOKE/CARBON|COMBINATION.*SMOKE", re.I), Category.DETECTOR, "smoke_co", True, False),
    (re.compile(r"SMOKE\s+DETECTOR", re.I), Category.DETECTOR, "smoke", False, False),
    (re.compile(r"JUNCTION\s+BOX", re.I), Category.JUNCTION_BOX, "junction_box", False, False),
    (re.compile(r"THREE\s+WAY.*DIMMER|WAY-DIMMER|3\s*-?\s*WAY.*DIMMER", re.I), Category.SWITCH, "three_way_dimmer", False, False),
    (re.compile(r"VACANCY", re.I), Category.SWITCH, "vacancy_sensor", False, False),
    (re.compile(r"ASTRONOMICAL|MOTION\s+SENSOR\s+SWITCH", re.I), Category.SWITCH, "astronomical_timer", False, False),
    (re.compile(r"SWITCH.*FAN|FAN\s+SWITCH", re.I), Category.SWITCH, "fan", False, False),
    (re.compile(r"SWITCH-DIMMER|DIMMER", re.I), Category.SWITCH, "dimmer", False, False),
    (re.compile(r"THREE\s+WAY|3\s*-?\s*WAY", re.I), Category.SWITCH, "three_way", False, False),
    (re.compile(r"ELECTRICAL\s+SWITCH|\bSWITCH\b", re.I), Category.SWITCH, "single_pole", False, False),
    (re.compile(r"FAN\s+COIL|\bFC\b", re.I), Category.RECEPTACLE, "fan_coil_dedicated", False, False),
    (re.compile(r"RANGE\s+HOOD", re.I), Category.RECEPTACLE, "range_hood", False, False),
    (re.compile(r"HALF\s+HOT|AFCI-HALF", re.I), Category.RECEPTACLE, "afci_half_hot", False, False),
    (re.compile(r"240\s*VOLT|240V", re.I), Category.RECEPTACLE, "gfci_240v", False, False),
    (re.compile(r"WATERPROOF|WEATHERPROOF", re.I), Category.RECEPTACLE, "gfci_weatherproof", False, False),
    (re.compile(r"MICROWAVE", re.I), Category.RECEPTACLE, "gfci_microwave", False, False),
    (re.compile(r"DISH\s*WASH", re.I), Category.RECEPTACLE, "gfci_dishwasher", False, False),
    (re.compile(r"ARC-FAULT|ARC FAULT|\bAFI\b|\bAFCI\b", re.I), Category.RECEPTACLE, "afci", False, False),
    (re.compile(r"GROUND\s+FAULT|\bGFI\b|\bGFCI\b", re.I), Category.RECEPTACLE, "gfci", False, False),
    (re.compile(r"DUPLEX\s+OUTLET|CONVENIENCE\s+OUTLET|\bOUTLET\b", re.I), Category.RECEPTACLE, "duplex", False, False),
]


def map_description(description: str) -> tuple[Category | None, str | None, bool, bool]:
    """Map legend description text → (category, subtype, combined, exclude)."""
    text = " ".join(description.split())
    for pattern, cat, subtype, combined, exclude in _RULES:
        if pattern.search(text):
            return cat, subtype, combined, exclude
    return None, None, False, False


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _bbox_gap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Chebyshev gap between two AABBs (0 if they touch or overlap)."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = max(0.0, max(ax0 - bx1, bx0 - ax1))
    dy = max(0.0, max(ay0 - by1, by0 - ay1))
    return max(dx, dy)


def _inflate(b: tuple[float, float, float, float], pad: float) -> tuple[float, float, float, float]:
    return (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)


def _center(b: tuple[float, float, float, float]) -> tuple[float, float]:
    return (0.5 * (b[0] + b[2]), 0.5 * (b[1] + b[3]))


def _y_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    return max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _seg_bbox(s: Segment) -> tuple[float, float, float, float]:
    return (min(s.x0, s.x1), min(s.y0, s.y1), max(s.x0, s.x1), max(s.y0, s.y1))


def _fill_bbox(f: FillPath) -> tuple[float, float, float, float]:
    return (f.x0, f.y0, f.x1, f.y1)


def _seg_len(s: Segment) -> float:
    return math.hypot(s.x1 - s.x0, s.y1 - s.y0)


def find_legend_title(ctx: PageContext) -> BBox:
    """Find the electrical ``LEGEND`` title (not ``FLOOR FINISH LEGEND``)."""
    best: Word | None = None
    for span in ctx.spans:
        if not span.is_bold or span.size < _LEGEND_TITLE_MIN_SIZE:
            continue
        text = " ".join(span.text.split()).upper()
        if text != "LEGEND":
            # Some sheets may say "ELECTRICAL LEGEND"; accept if it ends with LEGEND
            # and does not contain FLOOR/FINISH.
            if "LEGEND" not in text or "FLOOR" in text or "FINISH" in text:
                continue
        if best is None or span.size > best.size:
            best = span
    if best is None:
        raise ValueError(f"page {ctx.page_index}: electrical LEGEND title not found")
    x0, y0, x1, y1 = best.bbox
    return BBox(x0=x0, y0=y0, x1=x1, y1=y1)


def _legend_region(ctx: PageContext, title: BBox) -> BBox:
    """Approximate the legend cell: frame verticals + content height under title."""
    # Vertical frame lines near the title (full-page length preferred).
    xs: list[float] = []
    for seg in ctx.black_segments:
        if abs(seg.x1 - seg.x0) > 1.5:
            continue
        length = abs(seg.y1 - seg.y0)
        if length < 400:
            continue
        xs.append(0.5 * (seg.x0 + seg.x1))
    xs = sorted(set(round(x) for x in xs))
    cx = 0.5 * (title.x0 + title.x1)
    left = max((x for x in xs if x < title.x0 + 5), default=title.x0 - 20)
    right = min((x for x in xs if x > title.x1 - 5), default=title.x0 + 420)

    # Bottom: attic-access label if present below title, else a generous band.
    bottom = title.y0 + 620.0
    for span in ctx.spans:
        if "ATTIC ACCESS" in span.text.upper() and span.bbox[1] > title.y1:
            if left - 5 <= span.bbox[0] <= right + 5:
                bottom = max(bottom, span.bbox[3] + 10.0)
                break
    # Also stop before a far-below horizontal frame that crosses the cell.
    for seg in ctx.black_segments:
        if abs(seg.y1 - seg.y0) > 1.5:
            continue
        y = 0.5 * (seg.y0 + seg.y1)
        if y <= title.y1 + 40 or y > title.y0 + 700:
            continue
        sx0, sx1 = min(seg.x0, seg.x1), max(seg.x0, seg.x1)
        if sx0 <= left + 20 and sx1 >= right - 20 and abs(seg.x1 - seg.x0) > 300:
            # Major cell divider under the legend.
            if title.y1 + 200 < y < bottom:
                bottom = y - 2.0

    return BBox(x0=left + 2.0, y0=title.y1 + 4.0, x1=right - 2.0, y1=bottom)


# ---------------------------------------------------------------------------
# Symbol clustering inside the legend
# ---------------------------------------------------------------------------


@dataclass
class _SymbolBlob:
    bbox: tuple[float, float, float, float]
    segment_ids: list[int]
    fill_ids: list[int]


def _cluster_legend_symbols(ctx: PageContext, region: BBox) -> list[_SymbolBlob]:
    """Cluster black strokes/fills in the legend into per-row symbol blobs."""
    items: list[tuple[str, int, tuple[float, float, float, float]]] = []

    for i, seg in enumerate(ctx.black_segments):
        if _seg_len(seg) > _LONG_SEG_PT:
            continue  # underlines / column rules / wiring dashes (handled later)
        bb = _seg_bbox(seg)
        cx, cy = _center(bb)
        if not (region.x0 <= cx <= region.x1 and region.y0 <= cy <= region.y1):
            continue
        items.append(("s", i, _inflate(bb, 0.4)))

    for i, fill in enumerate(ctx.black_fills):
        bb = _fill_bbox(fill)
        cx, cy = _center(bb)
        if not (region.x0 <= cx <= region.x1 and region.y0 <= cy <= region.y1):
            continue
        items.append(("f", i, bb))

    if not items:
        return []

    parent = list(range(len(items)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def unite(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _bbox_gap(items[i][2], items[j][2]) < _SYMBOL_GAP_PT:
                unite(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(items)):
        groups[find(i)].append(i)

    blobs: list[_SymbolBlob] = []
    for members in groups.values():
        bbs = [items[i][2] for i in members]
        x0 = min(b[0] for b in bbs)
        y0 = min(b[1] for b in bbs)
        x1 = max(b[2] for b in bbs)
        y1 = max(b[3] for b in bbs)
        w, h = x1 - x0, y1 - y0
        if w * h < _MIN_SYMBOL_AREA_PT2:
            continue
        if w > _MAX_SYMBOL_WIDTH_PT or h > _MAX_SYMBOL_HEIGHT_PT:
            continue
        # Attic access panel: large rectangle (~46x34) with diagonals — exclude by
        # pairing with description later; keep for now if under size cap.
        seg_ids = [items[i][1] for i in members if items[i][0] == "s"]
        fill_ids = [items[i][1] for i in members if items[i][0] == "f"]
        blobs.append(_SymbolBlob(bbox=(x0, y0, x1, y1), segment_ids=seg_ids, fill_ids=fill_ids))

    # Second pass: merge blobs that are still close (fan blades sometimes sit
    # just over the gap after the long-seg filter removed connecting arcs).
    blobs = _merge_close_blobs(blobs, gap=3.0)
    return blobs


def _merge_close_blobs(blobs: list[_SymbolBlob], gap: float) -> list[_SymbolBlob]:
    if not blobs:
        return []
    parent = list(range(len(blobs)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(len(blobs)):
        for j in range(i + 1, len(blobs)):
            if _bbox_gap(blobs[i].bbox, blobs[j].bbox) < gap:
                # Only merge if the combined size still looks like one symbol.
                x0 = min(blobs[i].bbox[0], blobs[j].bbox[0])
                y0 = min(blobs[i].bbox[1], blobs[j].bbox[1])
                x1 = max(blobs[i].bbox[2], blobs[j].bbox[2])
                y1 = max(blobs[i].bbox[3], blobs[j].bbox[3])
                if (x1 - x0) <= _MAX_SYMBOL_WIDTH_PT and (y1 - y0) <= _MAX_SYMBOL_HEIGHT_PT:
                    parent[find(j)] = find(i)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(blobs)):
        groups[find(i)].append(i)

    merged: list[_SymbolBlob] = []
    for idxs in groups.values():
        x0 = min(blobs[i].bbox[0] for i in idxs)
        y0 = min(blobs[i].bbox[1] for i in idxs)
        x1 = max(blobs[i].bbox[2] for i in idxs)
        y1 = max(blobs[i].bbox[3] for i in idxs)
        segs: list[int] = []
        fills: list[int] = []
        for i in idxs:
            segs.extend(blobs[i].segment_ids)
            fills.extend(blobs[i].fill_ids)
        merged.append(_SymbolBlob(bbox=(x0, y0, x1, y1), segment_ids=segs, fill_ids=fills))
    return merged


# ---------------------------------------------------------------------------
# Description blocks
# ---------------------------------------------------------------------------


@dataclass
class _DescBlock:
    text: str
    bbox: tuple[float, float, float, float]


def _description_blocks(ctx: PageContext, region: BBox) -> list[_DescBlock]:
    """Group ~9.6 pt legend description spans into multi-line blocks."""
    lines: list[Word] = []
    for span in ctx.spans:
        if not (_DESC_SIZE_MIN <= span.size <= _DESC_SIZE_MAX):
            continue
        cx, cy = _center(span.bbox)
        if not (region.x0 <= cx <= region.x1 and region.y0 <= cy <= region.y1):
            continue
        text = span.text.strip()
        if not text:
            continue
        # Skip the big LEGEND title if size slipped through.
        if text.upper() == "LEGEND":
            continue
        lines.append(span)

    if not lines:
        return []

    lines.sort(key=lambda w: (w.bbox[1], w.bbox[0]))
    used = [False] * len(lines)
    blocks: list[_DescBlock] = []

    for i, seed in enumerate(lines):
        if used[i]:
            continue
        # Skip free-floating NOTE paragraphs (no symbol pairing expected as seed
        # of a column description that starts with NOTE:).
        if seed.text.upper().startswith("NOTE"):
            used[i] = True
            continue

        group = [seed]
        used[i] = True
        # Grow only by *consecutive* lines: each new line must sit within
        # _DESC_LINE_GAP_PT of the previous line's bottom. Checking against the
        # whole group height would chain an entire column into one block.
        while True:
            last = group[-1]
            next_j: int | None = None
            next_y = 1e18
            for j, other in enumerate(lines):
                if used[j]:
                    continue
                if abs(other.bbox[0] - seed.bbox[0]) > _DESC_X_ALIGN_PT:
                    if abs(other.bbox[0] - last.bbox[0]) > _DESC_X_ALIGN_PT:
                        continue
                # Must be below (or barely overlapping) the last line.
                if other.bbox[1] < last.bbox[1] - 1.0:
                    continue
                gap = other.bbox[1] - last.bbox[3]
                if gap > _DESC_LINE_GAP_PT:
                    continue
                if other.bbox[1] < next_y:
                    next_y = other.bbox[1]
                    next_j = j
            if next_j is None:
                break
            # Cap description height so a dense column cannot runaway-merge.
            if lines[next_j].bbox[3] - group[0].bbox[1] > 55.0:
                break
            group.append(lines[next_j])
            used[next_j] = True

        group.sort(key=lambda w: (w.bbox[1], w.bbox[0]))
        # Deduplicate identical span bboxes.
        texts: list[str] = []
        seen: set[tuple[str, int, int]] = set()
        for w in group:
            key = (w.text.strip(), round(w.bbox[0]), round(w.bbox[1]))
            if key in seen:
                continue
            seen.add(key)
            texts.append(w.text.strip())
        text = " ".join(texts)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 3:
            continue
        x0 = min(w.bbox[0] for w in group)
        y0 = min(w.bbox[1] for w in group)
        x1 = max(w.bbox[2] for w in group)
        y1 = max(w.bbox[3] for w in group)
        blocks.append(_DescBlock(text=text, bbox=(x0, y0, x1, y1)))

    return blocks


def _codes_near(
    ctx: PageContext,
    symbol_bbox: tuple[float, float, float, float],
    peers: list[tuple[float, float, float, float]] | None = None,
) -> list[str]:
    """Collect small code tokens (GFI, 3D, VP, +84, …) near a legend symbol.

    If ``peers`` is given, a token is kept only when this symbol is the closest
    peer — stops ``SD/MA`` from attaching to the junction-box row below.
    """
    sx0, sy0, sx1, sy1 = symbol_bbox
    search = _inflate(symbol_bbox, _CODE_RADIUS_PT)
    tokens: list[str] = []
    seen: set[str] = set()
    for word in ctx.words:
        if word.size > _CODE_SIZE_MAX:
            continue
        cx, cy = _center(word.bbox)
        if not (search[0] <= cx <= search[2] and search[1] <= cy <= search[3]):
            continue
        # Codes sit above or beside the glyph, not deep into the next row.
        if cy > sy1 + 8.0:
            continue
        if peers:
            my_dist = math.hypot(cx - 0.5 * (sx0 + sx1), cy - 0.5 * (sy0 + sy1))
            closer_peer = False
            for pb in peers:
                if pb == symbol_bbox:
                    continue
                pd = math.hypot(cx - 0.5 * (pb[0] + pb[2]), cy - 0.5 * (pb[1] + pb[3]))
                if pd + 0.5 < my_dist:
                    closer_peer = True
                    break
            if closer_peer:
                continue
        raw = word.text.strip()
        if not raw or raw in seen:
            continue
        if re.fullmatch(r"[^\w+/\"]+", raw):
            continue
        seen.add(raw)
        tokens.append(raw)
    return tokens


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _pair_score(
    symbol: tuple[float, float, float, float],
    desc: tuple[float, float, float, float],
) -> float | None:
    """Score a symbol↔description pairing; lower is better. None = incompatible.

    Normal rows: description sits to the **right** of the symbol with y-overlap.
    Large centered symbols (ceiling fan): description sits **below** the symbol.
    """
    sx0, sy0, sx1, sy1 = symbol
    dx0, dy0, dx1, dy1 = desc

    # --- right-side pairing (switches, receptacles, lights) ---
    dx = dx0 - sx1
    ov = _y_overlap(symbol, desc)
    if -10.0 <= dx <= _PAIR_MAX_DX_PT and dx0 >= sx0 - 5.0:
        y_dist = 0.0
        if ov < _PAIR_Y_OVERLAP_MIN_PT:
            y_dist = abs(dy0 - sy0)
            if y_dist > 22.0:
                pass  # try below-pairing instead
            else:
                return abs(dx) + y_dist * 2.0 - ov
        else:
            return abs(dx) - ov

    # --- below pairing (ceiling fan caption under the blades) ---
    # Description left edge near symbol left, top just under symbol bottom.
    if dy0 >= sy1 - 4.0 and dy0 <= sy1 + 40.0:
        if abs(dx0 - sx0) < 40.0 or (sx0 <= dx0 <= sx1 + 10.0):
            return 100.0 + (dy0 - sy1) + abs(dx0 - sx0) * 0.1

    return None


def _desc_text_for_symbol(
    ctx: PageContext,
    region: BBox,
    blob: _SymbolBlob,
    peers: list[_SymbolBlob],
) -> str:
    """Collect description text owned by one legend symbol.

    Vertical ownership: from the midpoint to the previous same-column peer down
    to the midpoint to the next peer. That stops row text from bleeding when
    inter-row gaps are as tight as multi-line gaps (~8–12 pt).
    """
    sx0, sy0, sx1, sy1 = blob.bbox
    scx = 0.5 * (sx0 + sx1)

    # Peers in the same column (symbol centers within ~40 pt in x).
    same_col = [
        p
        for p in peers
        if abs(0.5 * (p.bbox[0] + p.bbox[2]) - scx) < 40.0
    ]
    same_col.sort(key=lambda p: p.bbox[1])

    y_lo = region.y0
    y_hi = region.y1
    for i, p in enumerate(same_col):
        if p is blob or (
            abs(p.bbox[0] - sx0) < 0.5 and abs(p.bbox[1] - sy0) < 0.5
        ):
            if i > 0:
                prev = same_col[i - 1]
                y_lo = 0.5 * (prev.bbox[3] + sy0)
            if i + 1 < len(same_col):
                nxt = same_col[i + 1]
                y_hi = 0.5 * (sy1 + nxt.bbox[1])
            break

    # Text search band: prefer to the right of the symbol; also allow below for
    # large centered captions (ceiling fan).
    spans: list[Word] = []
    for span in ctx.spans:
        if not (_DESC_SIZE_MIN <= span.size <= _DESC_SIZE_MAX):
            continue
        cx, cy = _center(span.bbox)
        if not (region.x0 <= cx <= region.x1 and y_lo <= cy <= y_hi):
            continue
        text = span.text.strip()
        if not text or text.upper() == "LEGEND" or text.upper().startswith("NOTE"):
            continue
        right_of = (
            span.bbox[0] >= sx1 - 5.0
            and span.bbox[0] <= sx1 + _PAIR_MAX_DX_PT + 30.0
            # Keep right-side captions near the glyph; the ownership band alone
            # still leaks the previous row's last line into the next symbol.
            and span.bbox[1] <= sy1 + 18.0
            and span.bbox[3] >= sy0 - 4.0
        )
        below = (
            span.bbox[1] >= sy1 - 2.0
            and span.bbox[1] <= sy1 + 45.0
            and span.bbox[0] >= sx0 - 10.0
            and span.bbox[0] <= sx1 + 20.0
            and (sx1 - sx0) > 40.0  # only for large symbols (ceiling fan)
        )
        if right_of or below:
            spans.append(span)

    if not spans:
        return ""

    # Keep the leftmost description column only (avoid grabbing the next column).
    spans.sort(key=lambda w: (w.bbox[0], w.bbox[1]))
    col_x = spans[0].bbox[0]
    col = [s for s in spans if abs(s.bbox[0] - col_x) <= _DESC_X_ALIGN_PT]
    col.sort(key=lambda w: (w.bbox[1], w.bbox[0]))

    parts: list[str] = []
    seen: set[tuple[str, int, int]] = set()
    for w in col:
        key = (w.text.strip(), round(w.bbox[0]), round(w.bbox[1]))
        if key in seen:
            continue
        seen.add(key)
        parts.append(w.text.strip())
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def extract_legend(ctx: PageContext) -> list[LegendEntry]:
    """Find the electrical LEGEND (not floor finish) and parse each row.

    Each entry carries symbol geometry (for templates) and description text.
    Plumbing, attic access, and wiring rows are omitted (SPEC §1).
    """
    title = find_legend_title(ctx)
    region = _legend_region(ctx, title)
    blobs = _cluster_legend_symbols(ctx, region)

    entries: list[LegendEntry] = []
    kept_blobs: list[_SymbolBlob] = []

    for blob in sorted(blobs, key=lambda b: (b.bbox[1], b.bbox[0])):
        text = _desc_text_for_symbol(ctx, region, blob, blobs)
        if len(text) < 3:
            continue
        cat, subtype, combined, exclude = map_description(text)
        if exclude:
            continue
        peer_bbs = [b.bbox for b in blobs]
        codes = _codes_near(ctx, blob.bbox, peers=peer_bbs)
        code_join = " ".join(codes).upper()
        if any(t in code_join.split() for t in ("CW", "HW", "HB", "SOV")):
            # Plumbing stub symbols — always exclude (SPEC §1).
            continue
        # Tiny leftover geometry with no recognizable electrical description.
        if cat is None and not any(
            k in text.upper()
            for k in (
                "SWITCH",
                "OUTLET",
                "FAN",
                "LIGHT",
                "SMOKE",
                "JUNCTION",
                "DETECT",
                "RECESSED",
                "PENDANT",
            )
        ):
            continue
        # Continuation lines of a multi-line caption already owned by a taller
        # neighbor (fan-coil "TO BOTTOM OF UNIT…") — skip weak duplex leftovers.
        if text.upper().startswith("TO BOTTOM OF UNIT"):
            continue

        # Dedup: same category/subtype with heavily overlapping symbol bbox.
        dup = False
        for prev, prev_blob in zip(entries, kept_blobs, strict=True):
            if prev.category == cat and prev.subtype == subtype:
                if _bbox_gap(prev_blob.bbox, blob.bbox) < 8.0:
                    dup = True
                    break
                # Same description text within a few pt vertically.
                if prev.description == text and abs(prev.symbol_bbox.y0 - blob.bbox[1]) < 25.0:
                    dup = True
                    break
        if dup:
            continue

        entry_id = str(uuid.uuid4())
        entries.append(
            LegendEntry(
                id=entry_id,
                description=text,
                codes=codes,
                category=cat,
                subtype=subtype,
                combined=combined,
                symbol_bbox=BBox(
                    x0=blob.bbox[0],
                    y0=blob.bbox[1],
                    x1=blob.bbox[2],
                    y1=blob.bbox[3],
                ),
                interpreted_by="rules",
            )
        )
        kept_blobs.append(blob)

    _BLOB_CACHE[id(ctx)] = {e.id: b for e, b in zip(entries, kept_blobs, strict=True)}

    logger.info(
        "page %s: legend entries=%d (region y=%.0f..%.0f)",
        ctx.page_index,
        len(entries),
        region.y0,
        region.y1,
    )
    return entries


# page-context object id → entry_id → blob (filled by extract_legend)
_BLOB_CACHE: dict[int, dict[str, _SymbolBlob | None]] = {}


def legend_templates(ctx: PageContext, entries: list[LegendEntry]) -> dict[str, LegendTemplate]:
    """Build vector templates keyed by legend entry id.

    Primitives are the black segments/fills that formed the symbol cluster.
    Classification rasterizes these at 1:1 scale (same size as plan symbols).
    """
    cache = _BLOB_CACHE.get(id(ctx), {})
    templates: dict[str, LegendTemplate] = {}

    for entry in entries:
        blob = cache.get(entry.id)
        if blob is None:
            # Rebuild by bbox search if cache missed (e.g. entries came from LLM).
            blob = _blob_at(ctx, entry.symbol_bbox)
        if blob is None:
            templates[entry.id] = LegendTemplate(
                entry_id=entry.id,
                bbox=(
                    entry.symbol_bbox.x0,
                    entry.symbol_bbox.y0,
                    entry.symbol_bbox.x1,
                    entry.symbol_bbox.y1,
                ),
            )
            continue
        segs = [ctx.black_segments[i] for i in blob.segment_ids]
        fills = [ctx.black_fills[i] for i in blob.fill_ids]
        templates[entry.id] = LegendTemplate(
            entry_id=entry.id,
            bbox=blob.bbox,
            segments=segs,
            fills=fills,
        )
    return templates


def _blob_at(ctx: PageContext, bbox: BBox) -> _SymbolBlob | None:
    """Fallback: recluster legend and pick the blob overlapping ``bbox``."""
    try:
        title = find_legend_title(ctx)
        region = _legend_region(ctx, title)
    except ValueError:
        return None
    target = (bbox.x0, bbox.y0, bbox.x1, bbox.y1)
    best: _SymbolBlob | None = None
    best_ov = 0.0
    for blob in _cluster_legend_symbols(ctx, region):
        ov = _y_overlap(blob.bbox, target)  # rough; use area overlap
        x_ov = max(0.0, min(blob.bbox[2], target[2]) - max(blob.bbox[0], target[0]))
        area = x_ov * max(0.0, min(blob.bbox[3], target[3]) - max(blob.bbox[1], target[1]))
        if area > best_ov:
            best_ov = area
            best = blob
    return best
