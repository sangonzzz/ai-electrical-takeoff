"""interpret_legend: Claude refines rule-based legend entries (WHAT only)."""

from __future__ import annotations

import json
import logging

from takeoff_engine.llm.client import ClaudeClient, make_client
from takeoff_engine.llm.prompts import PROMPT_LEGEND, load_prompt, taxonomy_block
from takeoff_engine.llm.schemas import LegendInterpretResponse
from takeoff_engine.models import Category, LegendEntry, LlmUsage, SUBTYPES

logger = logging.getLogger(__name__)


def interpret_legend(
    entries: list[LegendEntry],
    legend_png: bytes,
    *,
    usage: LlmUsage | None = None,
    warnings: list[str] | None = None,
    client: ClaudeClient | None = None,
) -> list[LegendEntry]:
    """Map legend rows to category/subtype via Claude; merge with rules.

    Without an API key, returns the rule-based entries unchanged and records a
    warning. Disagreements between rules and LLM are logged as warnings; the
    LLM value wins when it provides a valid category/subtype.
    """
    warn_sink = warnings if warnings is not None else []
    cl = client or make_client(usage=usage)

    if not entries:
        return []

    if not cl.available:
        cl.warn_unavailable("interpret_legend")
        warn_sink.extend(cl.warnings)
        return list(entries)

    system = load_prompt(PROMPT_LEGEND)
    payload = [
        {
            "entry_id": e.id,
            "description": e.description,
            "codes": e.codes,
            "rules_category": e.category.value if e.category else None,
            "rules_subtype": e.subtype,
            "rules_combined": e.combined,
        }
        for e in entries
    ]
    user_text = (
        f"{taxonomy_block()}\n\n"
        "Interpret each legend entry. The attached image is the legend crop.\n\n"
        f"Entries JSON:\n{json.dumps(payload, indent=2)}"
    )

    response = cl.call_structured(
        model=cl.settings.anthropic_model,
        prompt_version=PROMPT_LEGEND,
        system=system,
        user_text=user_text,
        response_model=LegendInterpretResponse,
        images=[legend_png],
        cache_extra={"entry_ids": [e.id for e in entries]},
    )
    warn_sink.extend(cl.warnings)

    by_id = {item.entry_id: item for item in response.entries}
    merged: list[LegendEntry] = []
    for entry in entries:
        item = by_id.get(entry.id)
        if item is None:
            msg = f"LLM legend response missing entry_id={entry.id!r}; keeping rules"
            logger.warning(msg)
            warn_sink.append(msg)
            merged.append(entry)
            continue
        merged.append(_merge_entry(entry, item, warn_sink))

    missing_llm = set(by_id) - {e.id for e in entries}
    for mid in sorted(missing_llm):
        msg = f"LLM legend returned unknown entry_id={mid!r}; ignored"
        logger.warning(msg)
        warn_sink.append(msg)

    return merged


def _merge_entry(
    rules: LegendEntry,
    llm: object,
    warn_sink: list[str],
) -> LegendEntry:
    """LLM refines rules; disagreements become warnings."""
    # llm is LegendEntryInterpretation; duck-typed to avoid circular imports in typing
    llm_cat = getattr(llm, "category", None)
    llm_sub = getattr(llm, "subtype", None)
    llm_combined = bool(getattr(llm, "combined", False))
    raw_meanings = getattr(llm, "code_meanings", None) or []
    if hasattr(llm, "meanings_dict"):
        code_meanings = llm.meanings_dict()  # type: ignore[union-attr]
    elif isinstance(raw_meanings, dict):
        code_meanings = raw_meanings
    else:
        code_meanings = {
            getattr(m, "code", m.get("code") if isinstance(m, dict) else ""): (
                getattr(m, "meaning", m.get("meaning") if isinstance(m, dict) else "")
            )
            for m in raw_meanings
        }
    reason = getattr(llm, "reason", "")

    rules_cat = rules.category.value if rules.category else None
    rules_sub = rules.subtype

    if llm_cat is not None and rules_cat is not None and llm_cat != rules_cat:
        msg = (
            f"Legend {rules.id}: category disagreement rules={rules_cat!r} "
            f"llm={llm_cat!r} ({reason})"
        )
        logger.warning(msg)
        warn_sink.append(msg)
    if (
        llm_sub is not None
        and rules_sub is not None
        and llm_sub != rules_sub
        and (llm_cat is None or llm_cat == rules_cat or rules_cat is None)
    ):
        msg = (
            f"Legend {rules.id}: subtype disagreement rules={rules_sub!r} "
            f"llm={llm_sub!r} ({reason})"
        )
        logger.warning(msg)
        warn_sink.append(msg)

    # Prefer LLM when it supplies a valid category; else keep rules
    final_cat: Category | None = rules.category
    final_sub: str | None = rules.subtype
    interpreted_by = rules.interpreted_by

    if llm_cat is not None:
        try:
            final_cat = Category(llm_cat)
            interpreted_by = "llm"
        except ValueError:
            msg = f"Legend {rules.id}: invalid LLM category {llm_cat!r}; keeping rules"
            logger.warning(msg)
            warn_sink.append(msg)

    if llm_sub is not None and final_cat is not None:
        allowed = SUBTYPES.get(final_cat.value, [])
        if llm_sub in allowed:
            final_sub = llm_sub
            interpreted_by = "llm"
        else:
            msg = (
                f"Legend {rules.id}: LLM subtype {llm_sub!r} not allowed for "
                f"{final_cat.value}; keeping {final_sub!r}"
            )
            logger.warning(msg)
            warn_sink.append(msg)
    elif llm_cat is not None and llm_sub is None:
        # Explicit null subtype from LLM (non-component or unknown subtype)
        final_sub = None

    notes_codes = list(rules.codes)
    # Preserve codes from rules; meanings stay in reason/evidence via description notes
    # We append code meaning hints into description only if empty — keep description stable.
    _ = code_meanings  # available for callers via warnings/reason logging
    if code_meanings:
        logger.info(
            "Legend %s code meanings: %s",
            rules.id,
            code_meanings,
        )

    return LegendEntry(
        id=rules.id,
        description=rules.description,
        codes=notes_codes,
        category=final_cat,
        subtype=final_sub,
        combined=llm_combined if interpreted_by == "llm" else rules.combined,
        symbol_bbox=rules.symbol_bbox,
        interpreted_by=interpreted_by,  # type: ignore[arg-type]
    )
