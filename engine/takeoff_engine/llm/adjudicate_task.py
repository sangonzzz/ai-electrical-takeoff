"""adjudicate: batch ambiguous candidates; Claude returns labels only."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from takeoff_engine.llm.client import ClaudeClient, make_client
from takeoff_engine.llm.crops import render_candidate_crop, render_legend_thumbnails
from takeoff_engine.llm.prompts import PROMPT_ADJUDICATE, load_prompt, taxonomy_block
from takeoff_engine.llm.schemas import ALLOWED_ADJUDICATION_LABELS, AdjudicateResponse
from takeoff_engine.models import LegendEntry, LlmUsage
from takeoff_engine.types import Adjudication, Candidate

logger = logging.getLogger(__name__)

# Keep vision batches small enough for reliable tool JSON
DEFAULT_BATCH_SIZE = 6


def adjudicate(
    pdf_path: str | Path,
    page_index: int,
    candidates: list[Candidate],
    legend: list[LegendEntry],
    *,
    usage: LlmUsage | None = None,
    warnings: list[str] | None = None,
    client: ClaudeClient | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[Adjudication]:
    """Ask Claude to label ambiguous candidates from the allowed list.

    Never returns coordinates — only label, confidence, and reason.
    Without an API key, returns empty list and records a warning.
    """
    warn_sink = warnings if warnings is not None else []
    cl = client or make_client(usage=usage)

    if not candidates:
        return []

    if not cl.available:
        cl.warn_unavailable("adjudicate")
        warn_sink.extend(cl.warnings)
        return []

    system = load_prompt(PROMPT_ADJUDICATE)
    legend_thumbs = render_legend_thumbnails(pdf_path, page_index, legend)

    results: list[Adjudication] = []
    for start in range(0, len(candidates), batch_size):
        batch = candidates[start : start + batch_size]
        batch_results = _adjudicate_batch(
            cl,
            pdf_path=pdf_path,
            page_index=page_index,
            batch=batch,
            legend=legend,
            legend_thumbs=legend_thumbs,
            system=system,
            warn_sink=warn_sink,
        )
        results.extend(batch_results)

    return results


def _adjudicate_batch(
    cl: ClaudeClient,
    *,
    pdf_path: str | Path,
    page_index: int,
    batch: list[Candidate],
    legend: list[LegendEntry],
    legend_thumbs: list[tuple[str, bytes]],
    system: str,
    warn_sink: list[str],
) -> list[Adjudication]:
    images: list[bytes] = []
    image_guide: list[str] = []

    # Legend thumbnails first so the model sees the sheet's own symbols
    for i, (label, png) in enumerate(legend_thumbs):
        images.append(png)
        image_guide.append(f"Image {len(images)}: LEGEND thumbnail — {label}")

    for cand in batch:
        crop = render_candidate_crop(pdf_path, page_index, cand)
        images.append(crop)
        image_guide.append(
            f"Image {len(images)}: CANDIDATE id={cand.id} "
            f"(red outline; nearby text may include codes)"
        )

    legend_text = [
        {
            "id": e.id,
            "description": e.description,
            "codes": e.codes,
            "category": e.category.value if e.category else None,
            "subtype": e.subtype,
        }
        for e in legend
    ]
    cand_meta = [
        {
            "candidate_id": c.id,
            "features": {k: v for k, v in c.features.items() if k in {"codes", "match_score", "top_labels"}},
        }
        for c in batch
    ]

    user_text = (
        f"{taxonomy_block()}\n\n"
        "Label each CANDIDATE image. Images are ordered as listed below.\n"
        "Return one item per candidate_id.\n\n"
        f"Image guide:\n" + "\n".join(image_guide) + "\n\n"
        f"Legend entries JSON:\n{json.dumps(legend_text, indent=2)}\n\n"
        f"Candidates JSON:\n{json.dumps(cand_meta, indent=2)}"
    )

    response = cl.call_structured(
        model=cl.settings.anthropic_model,
        prompt_version=PROMPT_ADJUDICATE,
        system=system,
        user_text=user_text,
        response_model=AdjudicateResponse,
        images=images,
        cache_extra={
            "page_index": page_index,
            "candidate_ids": [c.id for c in batch],
        },
    )
    warn_sink.extend(cl.warnings)

    by_id = {item.candidate_id: item for item in response.items}
    out: list[Adjudication] = []
    for cand in batch:
        item = by_id.get(cand.id)
        if item is None:
            msg = f"LLM adjudication missing candidate_id={cand.id!r}"
            logger.warning(msg)
            warn_sink.append(msg)
            continue
        label = item.label
        if label not in ALLOWED_ADJUDICATION_LABELS:
            msg = f"LLM adjudication invalid label {label!r} for {cand.id}; skipped"
            logger.warning(msg)
            warn_sink.append(msg)
            continue
        out.append(
            Adjudication(
                candidate_id=cand.id,
                label=label,
                confidence=float(item.confidence),
                reason=item.reason,
            )
        )
    return out
