"""Pure metrics: count error, room exact-match, detection precision/recall.

No I/O and no network — safe for unit tests and CI.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from eval.taxonomy import HIGHLIGHT_CATEGORIES, category_of, type_key

# SPEC section 11: match same type within 10 pt.
MATCH_RADIUS_PT = 10.0

HIGHLIGHT_TYPES = HIGHLIGHT_CATEGORIES  # alias for report wording


@dataclass
class DetectionMark:
    """Minimal detection for matching (pred or truth)."""

    category: str
    subtype: str
    x: float
    y: float
    id: str | None = None
    room: str | None = None

    @property
    def key(self) -> str:
        return type_key(self.category, self.subtype)


@dataclass
class MatchResult:
    """Greedy nearest-neighbour matches within MATCH_RADIUS_PT, same type."""

    true_positives: list[tuple[DetectionMark, DetectionMark]] = field(default_factory=list)
    false_positives: list[DetectionMark] = field(default_factory=list)
    false_negatives: list[DetectionMark] = field(default_factory=list)

    def precision_recall_by_type(self) -> dict[str, dict[str, float]]:
        """Per ``category.subtype`` (and rolled-up category) precision / recall."""
        tp: dict[str, int] = {}
        fp: dict[str, int] = {}
        fn: dict[str, int] = {}

        def bump(d: dict[str, int], key: str) -> None:
            d[key] = d.get(key, 0) + 1
            cat = category_of(key)
            d[cat] = d.get(cat, 0) + 1

        for pred, _truth in self.true_positives:
            bump(tp, pred.key)
        for pred in self.false_positives:
            bump(fp, pred.key)
        for truth in self.false_negatives:
            bump(fn, truth.key)

        keys = sorted(set(tp) | set(fp) | set(fn))
        out: dict[str, dict[str, float]] = {}
        for k in keys:
            tpi, fpi, fni = tp.get(k, 0), fp.get(k, 0), fn.get(k, 0)
            prec = tpi / (tpi + fpi) if (tpi + fpi) else 0.0
            rec = tpi / (tpi + fni) if (tpi + fni) else 0.0
            out[k] = {
                "precision": prec,
                "recall": rec,
                "tp": float(tpi),
                "fp": float(fpi),
                "fn": float(fni),
            }
        return out

    def to_eval_marks(self) -> dict[str, Any]:
        """Shape consumed by ``render_overlay(..., eval_marks=...)``."""
        return {
            "true_positives": [
                {"x": p.x, "y": p.y, "type": p.key, "id": p.id} for p, _ in self.true_positives
            ],
            "false_positives": [
                {"x": p.x, "y": p.y, "type": p.key, "id": p.id} for p in self.false_positives
            ],
            "false_negatives": [
                {"x": t.x, "y": t.y, "type": t.key, "id": t.id} for t in self.false_negatives
            ],
        }


def _norm_room(name: str) -> str:
    return " ".join(name.strip().lower().split())


def count_errors(
    predicted: Mapping[str, Mapping[str, int]],
    truth: Mapping[str, Mapping[str, int]],
) -> dict[str, dict[str, int]]:
    """Per-room absolute count error for every key present in pred or truth.

    ``predicted`` / ``truth``: room_name -> {type_key -> count}.
    Returns room_name -> {type_key -> abs(pred - truth)}.
    """
    rooms = sorted(set(predicted) | set(truth), key=_norm_room)
    out: dict[str, dict[str, int]] = {}
    for room in rooms:
        pred_counts = predicted.get(room, {})
        truth_counts = truth.get(room, {})
        keys = set(pred_counts) | set(truth_counts)
        out[room] = {
            k: abs(int(pred_counts.get(k, 0)) - int(truth_counts.get(k, 0))) for k in sorted(keys)
        }
    return out


def room_exact_match_rate(
    predicted: Mapping[str, Mapping[str, int]],
    truth: Mapping[str, Mapping[str, int]],
    *,
    keys: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Fraction of rooms whose counts match truth exactly on the compared keys.

    If ``keys`` is None, compare the union of all subtype keys that appear in
    truth for that room (zeros in pred for missing keys). Rooms only in pred
    with any non-zero count count as mismatches; empty-only rooms in pred that
    are absent from truth are ignored.
    """
    # Align by normalized name but report using truth's spelling when possible.
    truth_by_norm = {_norm_room(r): (r, c) for r, c in truth.items()}
    pred_by_norm = {_norm_room(r): (r, c) for r, c in predicted.items()}

    matched = 0
    total = 0
    per_room: dict[str, bool] = {}

    for norm, (truth_name, truth_counts) in sorted(truth_by_norm.items()):
        pred_counts = pred_by_norm.get(norm, (truth_name, {}))[1]
        compare_keys = list(keys) if keys is not None else sorted(
            k for k, v in truth_counts.items() if int(v) != 0 or k in pred_counts
        )
        if not compare_keys:
            # Both empty for this room — treat as exact match.
            compare_keys = sorted(set(truth_counts) | set(pred_counts))
        ok = all(int(pred_counts.get(k, 0)) == int(truth_counts.get(k, 0)) for k in compare_keys)
        # Also fail if pred has extra non-zero keys not in the compare set when
        # keys was None: include all keys from both sides.
        if keys is None:
            all_keys = set(truth_counts) | set(pred_counts)
            ok = all(int(pred_counts.get(k, 0)) == int(truth_counts.get(k, 0)) for k in all_keys)
        per_room[truth_name] = ok
        total += 1
        if ok:
            matched += 1

    rate = matched / total if total else 1.0
    return {"rate": rate, "matched": matched, "total": total, "per_room": per_room}


def totals_vs_truth(
    predicted_totals: Mapping[str, int],
    truth_totals: Mapping[str, int],
) -> dict[str, dict[str, int]]:
    """Sheet-level totals: pred, truth, and signed error (pred - truth) per key."""
    keys = sorted(set(predicted_totals) | set(truth_totals))
    return {
        k: {
            "pred": int(predicted_totals.get(k, 0)),
            "truth": int(truth_totals.get(k, 0)),
            "error": int(predicted_totals.get(k, 0)) - int(truth_totals.get(k, 0)),
        }
        for k in keys
    }


def _dist(a: DetectionMark, b: DetectionMark) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def match_detections(
    predicted: Sequence[DetectionMark],
    truth: Sequence[DetectionMark],
    *,
    radius_pt: float = MATCH_RADIUS_PT,
) -> MatchResult:
    """Greedy match: same type_key, nearest unused truth within ``radius_pt``."""
    # Group truth by type for O(n*m_type) matching.
    truth_by_type: dict[str, list[DetectionMark]] = {}
    for t in truth:
        truth_by_type.setdefault(t.key, []).append(t)

    used: set[int] = set()  # id(truth mark)
    tps: list[tuple[DetectionMark, DetectionMark]] = []
    fps: list[DetectionMark] = []

    # Stable order: process preds by type then position so results are deterministic.
    preds_sorted = sorted(predicted, key=lambda p: (p.key, p.x, p.y, p.id or ""))

    for pred in preds_sorted:
        candidates = truth_by_type.get(pred.key, [])
        best: DetectionMark | None = None
        best_d = radius_pt + 1.0
        for t in candidates:
            if id(t) in used:
                continue
            d = _dist(pred, t)
            if d <= radius_pt and d < best_d:
                best = t
                best_d = d
        if best is not None:
            used.add(id(best))
            tps.append((pred, best))
        else:
            fps.append(pred)

    fns = [t for t in truth if id(t) not in used]
    return MatchResult(true_positives=tps, false_positives=fps, false_negatives=fns)


def aggregate_room_counts(
    room_counts: Mapping[str, Mapping[str, int]],
) -> dict[str, int]:
    """Sum per-room counts into sheet totals (subtype keys only)."""
    totals: dict[str, int] = {}
    for counts in room_counts.values():
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + int(v)
    return totals


def predicted_counts_from_takeoff_rows(
    rows: Iterable[Any],
) -> dict[str, dict[str, int]]:
    """Build room_name -> counts from TakeoffRow-like objects or dicts."""
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        if hasattr(row, "room_name"):
            name = row.room_name
            counts = dict(row.counts)
        else:
            name = row["room_name"]
            counts = dict(row.get("counts", {}))
        # Keep only category.subtype keys for fair compare with hand templates.
        out[name] = {k: int(v) for k, v in counts.items() if "." in k}
    return out
