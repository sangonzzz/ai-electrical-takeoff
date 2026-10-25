# Module: AI with Claude (`takeoff_engine/llm`)

Owner: Agente 4.

## What it does

Uses Claude for **WHAT** only — never WHERE:

1. **`interpret_legend(entries, legend_png)`** — refine rule-based legend rows
   (category, subtype, code meanings, combined flag).
2. **`adjudicate(pdf_path, page_index, candidates, legend)`** — label ambiguous
   symbol candidates from crops + legend thumbnails.
3. **`baseline_vision_takeoff(sheet_png, room_names)`** — LLM-only per-room
   counts for Agente 7’s “LLM alone vs hybrid” comparison (explicitly a baseline).

Geometry (Agente 2) owns positions. Without `ANTHROPIC_API_KEY` (or with
`ENABLE_LLM=false`) the engine still runs: rules-only legend, empty adjudication,
empty baseline counts, plus a warning.

## Why these models

| Task | Env var | Default | Why |
|------|---------|---------|-----|
| `interpret_legend` | `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | One vision call per sheet; accuracy on legend text + symbols matters. |
| `adjudicate` | `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Ambiguous crops need reliable subtype discrimination. |
| `baseline_vision_takeoff` | `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Fair demo vs hybrid — same class of vision model, not a weaker Haiku. |
| (reserved) | `ANTHROPIC_MODEL_CHEAP` | `claude-haiku-5-5` | Available on `Settings` for future high-volume text-only tasks. |

List prices used for `LlmUsage.cost_usd` (USD / MTok): Sonnet 5.5 $2 in / $10 out;
Haiku 5.5 $0.10 in / $0.50 out.

## Prompts

Versioned markdown under `engine/prompts/`:

| File | `prompt_version` | Role |
|------|------------------|------|
| `legend_v1.md` | `legend_v1` | Map legend rows; null allowed; no coordinates. |
| `adjudicate_v1.md` | `adjudicate_v1` | Label crops; allowed `category.subtype` or `not_a_component`. |
| `baseline_v1.md` | `baseline_v1` | Approximate room counts; labeled baseline-only. |

User messages also inject the taxonomy block from `SUBTYPES` so the model cannot
invent category strings.

## Structured output and validation

- Forced **tool use** (`submit_result`) with JSON Schema from Pydantic
  (`LegendInterpretResponse`, `AdjudicateResponse`, `BaselineVisionResponse`).
- Response validated with Pydantic; enums must match SPEC §2.
- On validation failure: **one** retry that includes the error text.
- Transport retries (max 3 attempts) only for 429, 5xx, timeouts, network /
  overloaded errors — exponential backoff with full jitter.
- Merge for legend: LLM refines rules; category/subtype disagreements append
  warnings; LLM wins when valid.

## Cache

`cache.py`: `sha256(model + prompt_version + text + image bytes + extra)`.
Disk store: `.cache/llm/{key}.json` (gitignored). Cache hits increment
`LlmUsage.cache_hits` and skip the API. Warm cache makes the demo deterministic
and cheap.

## Cost / tokens (expected per sheet, cold cache)

Rough estimates for Escondido sheets (vision + tool JSON):

| Call | Model | ~input tok | ~output tok | ~USD |
|------|-------|------------|-------------|------|
| legend ×1 | Sonnet 5.5 | 3–6k | 0.8–1.5k | 0.015–0.025 |
| adjudicate ×1–3 batches | Sonnet 5.5 | 8–25k | 0.5–1.5k | 0.02–0.07 |
| **sheet total (prod LLM)** | | | | **~0.04–0.10** |
| baseline (eval only) | Sonnet 5.5 | 5–15k | 1–3k | 0.03–0.06 |

With a warm disk cache, API calls drop to 0 and USD ≈ 0 for identical inputs.

## Why we never ask for coordinates

Vision LLMs are imprecise with positions, miscount dense symbols, and are
non-deterministic. These plans are fully vector: PyMuPDF gives exact geometry.
Claude only resolves meaning (legend semantics, ambiguous labels). Crops for
adjudication are rendered by us (~300 dpi, candidate outlined in red, context
pad ~18 pt); the model returns `label` + `confidence` + `reason` only.

## Public API notes for Agente 2 / 7

```python
from takeoff_engine.llm import interpret_legend, adjudicate, baseline_vision_takeoff
from takeoff_engine.models import LlmUsage

usage = LlmUsage()
warnings: list[str] = []
legend = interpret_legend(entries, legend_png, usage=usage, warnings=warnings)
labels = adjudicate(pdf, page, needs_review, legend, usage=usage, warnings=warnings)
# eval only:
baseline = baseline_vision_takeoff(sheet_png, room_names, usage=usage, warnings=warnings)
```

Optional kwargs keep the required signatures stable while letting the pipeline
fill `SheetResult.llm_usage` and `warnings`.

## Known limits

- Fixtures under `engine/tests/llm/fixtures/` are schema-faithful stand-ins until
  a real Anthropic response is recorded with Santiago’s API key.
- Adjudication batch size default is 6 crops (+ legend thumbs) per call.
- Legend thumbnails need valid `symbol_bbox` from Agente 2; degenerate boxes are skipped.
- Cost figures are estimates from published list prices, not invoices.
