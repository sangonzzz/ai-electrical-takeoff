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
| `interpret_legend` | `ANTHROPIC_MODEL_CHEAP` | `claude-haiku-5-5` | Measured identical category/subtype to Sonnet on Escondido Plan 1; ~15× cheaper, lower latency. |
| `adjudicate` | `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Ambiguous crops; **one batched call per sheet** (all `needs_review`). |
| `baseline_vision_takeoff` | `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Fair demo vs hybrid — same class of vision model. |

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

- **Tool use** (`submit_result`) with JSON Schema from Pydantic
  (`LegendInterpretResponse`, `AdjudicateResponse`, `BaselineVisionResponse`).
- **Claude Sonnet 5.5:** forced `tool_choice` (`tool` / `any`) returns HTTP 400.
  We use `tool_choice: auto` + `strict: true` on the tool, and the prompt
  requires calling `submit_result`. Free-form maps are lists of pairs so the
  schema can set `additionalProperties: false`.
- Response validated with Pydantic; enums must match SPEC §2.
- On validation failure (or missing tool call): **one** retry that includes the error text.
- Transport retries (max 3 attempts) only for 429, 5xx, timeouts, network /
  overloaded errors — exponential backoff with full jitter.
- Merge for legend: LLM refines rules; category/subtype disagreements append
  warnings; LLM wins when valid.

## Cache

`cache.py`: `sha256(model + prompt_version + text + image bytes + extra)`.
Disk store: `.cache/llm/{key}.json` (gitignored). Cache hits increment
`LlmUsage.cache_hits` and skip the API.

Pipeline mints fresh `uuid4` ids each run. Prompts use **stable content ids**
(`llm/ids.py`: legend description+codes+bbox; candidate page+bbox) so a second
`analyze_sheet` hits disk cache. Measured warm `llm_legend` ≈ 100–130 ms.

## Latency (measured 2026-10-26, local, 4 Escondido sheets)

| Mode | avg wall/sheet | LLM calls (4 sheets) | USD (4 sheets) |
|------|----------------|----------------------|----------------|
| Cold (Haiku legend) | ~41 s | 5 | ~$0.024 |
| Warm (disk cache) | ~24 s | 0 | $0 |

Cold `llm_legend` ≈ 14–18 s (Haiku). Remaining warm time is mostly geometry
(`candidates`/`classify` on pages 2–3), not Claude.

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

## Applying adjudications (`llm/apply.py`)

Pipeline calls `apply_adjudications(detections, adjs, mode="flag_only")`:

| Rule | Behavior |
|------|----------|
| Create | **Never** — only mutates existing detections |
| Delete | **Never** in `flag_only`; in `safe_relabel` only weak evidence (`match < 0.8` and no codes/tokens) on `not_a_component` |
| Strong evidence | `match_score >= 0.8` OR any `codes` / `text_tokens` — protected |
| Relabel | `flag_only`: no; `safe_relabel`: subtype within same category if strong |
| Exterior | Footprint EXT/WP filter remains `drop_outside_footprint` (Agente 2) |

Default is **`flag_only`** after LLM delete/relabel proved net-negative vs no-LLM.

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

- `legend_response.recorded.json` is a real Anthropic capture (Plan 1, 26 rows,
  ~6.6k in / 3.7k out / ~$0.05). Synthetic `legend_response.json` stays for
  offline merge-disagreement unit tests.
- Adjudication batch size default is 6 crops (+ legend thumbs) per call.
- Legend thumbnails need valid `symbol_bbox` from Agente 2; degenerate boxes are skipped.
- Cost figures use published list prices; recorded call cost is logged in fixture `_meta`.
- Repo `.env` is loaded automatically if `ANTHROPIC_API_KEY` is unset in the process.
