"""Accuracy from a reviewed-run corrections log (no spatial matching).

Mapping (detection entity only)::

    delete  → false positive   (system invented a mark the reviewer removed)
    create  → false negative   (system missed a mark the reviewer added)
    update with category/subtype change → misclassification
    update with room_id change          → room error

Position-only updates are ignored for these tallies. Fans and lights are
highlighted because reviewers weigh them most (SPEC).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from eval.taxonomy import HIGHLIGHT_CATEGORIES, type_key


def _cat(payload: Mapping[str, Any] | None) -> str | None:
    if not payload:
        return None
    c = payload.get("category")
    return str(c) if c is not None else None


def _sub(payload: Mapping[str, Any] | None) -> str | None:
    if not payload:
        return None
    s = payload.get("subtype")
    return str(s) if s is not None else None


def _type_key(payload: Mapping[str, Any] | None) -> str | None:
    c, s = _cat(payload), _sub(payload)
    if c and s:
        return type_key(c, s)
    return c


def _room_id(payload: Mapping[str, Any] | None) -> str | None:
    if not payload:
        return None
    rid = payload.get("room_id")
    return str(rid) if rid is not None else None


def _bump(d: dict[str, int], key: str | None) -> None:
    if not key:
        key = "unknown"
    d[key] = d.get(key, 0) + 1


def accuracy_from_corrections(
    corrections: Sequence[Mapping[str, Any]],
    *,
    predicted_counts_by_category: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Summarize detection corrections into FP / FN / misclass / room errors.

    ``predicted_counts_by_category`` is optional (active detections before
    review). When present, per-category rates use it as the denominator for
    FP and misclass/room rates; FN uses ``pred - fp + fn`` as estimated truth.
    """
    fp: dict[str, int] = {}
    fn: dict[str, int] = {}
    misclass: dict[str, int] = {}
    room_err: dict[str, int] = {}
    events: list[dict[str, Any]] = []

    for raw in corrections:
        if str(raw.get("entity", "detection")) not in {"detection", "detections"}:
            continue
        action = str(raw.get("action", "")).lower()
        before = raw.get("before") if isinstance(raw.get("before"), Mapping) else None
        after = raw.get("after") if isinstance(raw.get("after"), Mapping) else None

        if action == "delete":
            cat = _cat(before) or "unknown"
            _bump(fp, cat)
            events.append(
                {
                    "kind": "false_positive",
                    "category": cat,
                    "type": _type_key(before),
                    "entity_id": raw.get("entity_id"),
                }
            )
        elif action == "create":
            cat = _cat(after) or "unknown"
            _bump(fn, cat)
            events.append(
                {
                    "kind": "false_negative",
                    "category": cat,
                    "type": _type_key(after),
                    "entity_id": raw.get("entity_id"),
                }
            )
        elif action == "update":
            before_cat, after_cat = _cat(before), _cat(after)
            before_sub, after_sub = _sub(before), _sub(after)
            type_changed = (before_cat, before_sub) != (after_cat, after_sub) and (
                before_cat is not None or after_cat is not None
            )
            room_changed = _room_id(before) != _room_id(after)
            if type_changed:
                # Attribute to the system's original category (what it got wrong).
                cat = before_cat or after_cat or "unknown"
                _bump(misclass, cat)
                events.append(
                    {
                        "kind": "misclassification",
                        "category": cat,
                        "from_type": _type_key(before),
                        "to_type": _type_key(after),
                        "entity_id": raw.get("entity_id"),
                    }
                )
            if room_changed:
                cat = before_cat or after_cat or "unknown"
                _bump(room_err, cat)
                events.append(
                    {
                        "kind": "room_error",
                        "category": cat,
                        "from_room_id": _room_id(before),
                        "to_room_id": _room_id(after),
                        "entity_id": raw.get("entity_id"),
                    }
                )

    categories = sorted(
        set(fp) | set(fn) | set(misclass) | set(room_err) | set(predicted_counts_by_category or {})
    )
    by_category: dict[str, dict[str, Any]] = {}
    for cat in categories:
        row: dict[str, Any] = {
            "false_positives": fp.get(cat, 0),
            "false_negatives": fn.get(cat, 0),
            "misclassifications": misclass.get(cat, 0),
            "room_errors": room_err.get(cat, 0),
        }
        if predicted_counts_by_category is not None:
            pred_n = int(predicted_counts_by_category.get(cat, 0))
            row["predicted"] = pred_n
            est_truth = max(0, pred_n - row["false_positives"] + row["false_negatives"])
            row["estimated_truth"] = est_truth
            row["fp_rate"] = (row["false_positives"] / pred_n) if pred_n else 0.0
            row["fn_rate"] = (row["false_negatives"] / est_truth) if est_truth else 0.0
            row["misclass_rate"] = (row["misclassifications"] / pred_n) if pred_n else 0.0
            row["room_error_rate"] = (row["room_errors"] / pred_n) if pred_n else 0.0
        by_category[cat] = row

    highlight = {
        cat: by_category[cat]
        for cat in sorted(HIGHLIGHT_CATEGORIES)
        if cat in by_category
        or (predicted_counts_by_category and cat in predicted_counts_by_category)
    }
    # Ensure fans/lights appear even with zeros when we have predicted counts.
    if predicted_counts_by_category is not None:
        for cat in HIGHLIGHT_CATEGORIES:
            highlight.setdefault(
                cat,
                {
                    "false_positives": 0,
                    "false_negatives": 0,
                    "misclassifications": 0,
                    "room_errors": 0,
                    "predicted": int(predicted_counts_by_category.get(cat, 0)),
                    "estimated_truth": int(predicted_counts_by_category.get(cat, 0)),
                    "fp_rate": 0.0,
                    "fn_rate": 0.0,
                    "misclass_rate": 0.0,
                    "room_error_rate": 0.0,
                },
            )

    return {
        "false_positives": sum(fp.values()),
        "false_negatives": sum(fn.values()),
        "misclassifications": sum(misclass.values()),
        "room_errors": sum(room_err.values()),
        "by_category": by_category,
        "highlight": {k: highlight[k] for k in sorted(highlight)},
        "events": events,
    }


def predicted_category_counts(detections: Sequence[Any]) -> dict[str, int]:
    """Count active detections by category from SheetResult detections or dicts."""
    out: dict[str, int] = defaultdict(int)
    for d in detections:
        if hasattr(d, "status") and getattr(d, "status", None) == "deleted":
            continue
        if isinstance(d, Mapping):
            if d.get("status") == "deleted":
                continue
            cat = d.get("category")
        else:
            cat = d.category.value if hasattr(d.category, "value") else d.category
        if cat:
            out[str(cat)] += 1
    return dict(out)
