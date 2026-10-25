"""baseline_vision_takeoff: LLM-only counts for eval vs hybrid (presentation).

Clearly labeled as a baseline — not production detection. Geometry is ignored;
Claude estimates counts per room from a sheet raster.
"""

from __future__ import annotations

import json
import logging

from takeoff_engine.llm.client import ClaudeClient, make_client
from takeoff_engine.llm.prompts import PROMPT_BASELINE, load_prompt, taxonomy_block
from takeoff_engine.llm.schemas import BaselineVisionResponse
from takeoff_engine.models import LlmUsage

logger = logging.getLogger(__name__)


def baseline_vision_takeoff(
    sheet_png: bytes,
    room_names: list[str],
    *,
    usage: LlmUsage | None = None,
    warnings: list[str] | None = None,
    client: ClaudeClient | None = None,
) -> dict[str, dict[str, int]]:
    """LLM-only takeoff baseline for eval comparison (room -> counts).

    Returns ``{room_name: {count_key: n}}``. Without an API key, returns empty
    counts for each room and records a warning.
    """
    warn_sink = warnings if warnings is not None else []
    cl = client or make_client(usage=usage)

    empty = {name: {} for name in room_names}

    if not cl.available:
        cl.warn_unavailable("baseline_vision_takeoff")
        warn_sink.extend(cl.warnings)
        return empty

    # Fair presentation baseline: same primary vision model as production LLM tasks
    model = cl.settings.anthropic_model
    system = load_prompt(PROMPT_BASELINE)
    user_text = (
        "BASELINE ONLY — approximate visual counts, no coordinates.\n\n"
        f"{taxonomy_block()}\n\n"
        f"Room names (use exactly):\n{json.dumps(room_names, indent=2)}\n"
    )

    response = cl.call_structured(
        model=model,
        prompt_version=PROMPT_BASELINE,
        system=system,
        user_text=user_text,
        response_model=BaselineVisionResponse,
        images=[sheet_png],
        cache_extra={"room_names": list(room_names)},
        max_tokens=8192,
    )
    warn_sink.extend(cl.warnings)
    if response.notes:
        logger.info("baseline_vision notes: %s", response.notes[:400])

    result: dict[str, dict[str, int]] = {name: {} for name in room_names}
    known = set(room_names)
    for room in response.rooms:
        name = room.room_name
        if name not in known:
            msg = f"baseline_vision unknown room_name={name!r}; ignored"
            logger.warning(msg)
            warn_sink.append(msg)
            continue
        result[name] = room.counts_dict()

    for name in room_names:
        if name not in {r.room_name for r in response.rooms}:
            msg = f"baseline_vision missing room_name={name!r}; empty counts"
            logger.warning(msg)
            warn_sink.append(msg)

    return result
