"""Apply LLM adjudications under Santiago's safety rules.

Rules (2026-10-26):
- LLM may relabel **subtype** (same category) or set ``needs_review``.
- Never **delete** a detection that has strong geometric/text evidence
  (``match_score >= 0.8`` or any code / text token).
- Never **create** detections (apply only mutates the given list).
- Exterior / footprint filtering stays with ``drop_outside_footprint`` (EXT/WP).

When ``mode="flag_only"`` (default after net-negative eval): record
``llm_label`` / ``llm_reason`` and set ``needs_review``, but do not change
category/subtype and never drop rows. Legend interpretation stays separate.
"""

from __future__ import annotations

import logging
from typing import Literal

from takeoff_engine.models import Category, Detection, SUBTYPES
from takeoff_engine.types import Adjudication

logger = logging.getLogger(__name__)

STRONG_MATCH = 0.8

ApplyMode = Literal["flag_only", "safe_relabel"]


def has_strong_evidence(det: Detection) -> bool:
    """True when geometry/text evidence is strong enough to protect the row."""
    score = det.evidence.match_score
    if score is not None and score >= STRONG_MATCH:
        return True
    if det.codes:
        return True
    if det.evidence.text_tokens:
        return True
    return False


def apply_adjudications(
    detections: list[Detection],
    adjudications: list[Adjudication],
    *,
    mode: ApplyMode = "flag_only",
    warnings: list[str] | None = None,
) -> list[Detection]:
    """Merge adjudications into detections. Never creates new detections.

    ``flag_only`` (default): keep geometry labels; attach LLM opinion + needs_review.
    ``safe_relabel``: allow subtype (same category) changes; never delete strong
    evidence; ``not_a_component`` only drops weak-evidence rows.
    """
    warn = warnings if warnings is not None else []
    by_id = {a.candidate_id: a for a in adjudications}
    out: list[Detection] = []

    for det in detections:
        adj = by_id.get(det.id)
        if adj is None:
            out.append(det)
            continue

        if mode == "flag_only":
            out.append(_flag_only(det, adj))
            continue

        # ---- safe_relabel ----
        if adj.label == "not_a_component":
            if has_strong_evidence(det):
                msg = (
                    f"adjudicate refused delete of strong evidence id={det.id[:8]} "
                    f"({det.category.value}.{det.subtype}); flagging needs_review"
                )
                logger.warning(msg)
                warn.append(msg)
                out.append(_flag_only(det, adj, force_review=True))
            else:
                msg = (
                    f"adjudicate dropped weak detection id={det.id[:8]} "
                    f"({det.category.value}.{det.subtype}) as not_a_component"
                )
                logger.info(msg)
                warn.append(msg)
                # Explicit delete only for weak evidence
                continue
            continue

        if "." not in adj.label:
            out.append(_flag_only(det, adj))
            continue

        cat_s, sub = adj.label.split(".", 1)
        try:
            cat = Category(cat_s)
        except ValueError:
            out.append(_flag_only(det, adj))
            continue
        if sub not in SUBTYPES.get(cat.value, []):
            out.append(_flag_only(det, adj))
            continue

        strong = has_strong_evidence(det)
        if strong and cat != det.category:
            # May only relabel subtype within the same category when evidence is strong
            msg = (
                f"adjudicate refused category change on strong evidence "
                f"id={det.id[:8]} {det.category.value}->{cat.value}; "
                f"flagging needs_review"
            )
            logger.warning(msg)
            warn.append(msg)
            out.append(_flag_only(det, adj, force_review=True))
            continue

        if strong and cat == det.category and sub != det.subtype:
            out.append(
                det.model_copy(
                    update={
                        "subtype": sub,
                        "confidence": max(det.confidence, adj.confidence),
                        "source": "llm",
                        "needs_review": adj.confidence < 0.7,
                        "evidence": det.evidence.model_copy(
                            update={
                                "llm_label": adj.label,
                                "llm_reason": adj.reason,
                            }
                        ),
                    }
                )
            )
            continue

        if not strong:
            # Weak evidence: allow full category.subtype relabel (still no create)
            out.append(
                det.model_copy(
                    update={
                        "category": cat,
                        "subtype": sub,
                        "confidence": max(det.confidence, adj.confidence),
                        "source": "llm",
                        "needs_review": adj.confidence < 0.7,
                        "evidence": det.evidence.model_copy(
                            update={
                                "llm_label": adj.label,
                                "llm_reason": adj.reason,
                            }
                        ),
                    }
                )
            )
            continue

        out.append(_flag_only(det, adj))

    return out


def _flag_only(
    det: Detection,
    adj: Adjudication,
    *,
    force_review: bool = True,
) -> Detection:
    """Attach LLM opinion without changing category/subtype or dropping the row."""
    return det.model_copy(
        update={
            "needs_review": True if force_review else det.needs_review or adj.confidence < 0.7,
            "evidence": det.evidence.model_copy(
                update={
                    "llm_label": adj.label,
                    "llm_reason": adj.reason,
                }
            ),
        }
    )
