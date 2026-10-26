# From Agente 4 → Agente 1

Santiago asked A4 to profile + speed up LLM (engine freeze: no detection-rule changes).

## Changes (llm/ only)

1. Legend → Haiku (`ANTHROPIC_MODEL_CHEAP`) after Plan 1 parity vs Sonnet (0 diffs).
2. Adjudicate default = **one API call per sheet** (`DEFAULT_BATCH_SIZE=10000`).
3. Stable prompt ids so `.cache/llm` hits on second run (uuid4 was busting cache).
4. `transform_schema` for Sonnet 5.5 strict tools — **adjudicate was 400’ing** on
   `minimum`/`maximum` for `confidence`; now works (Plan 3 may gain `llm_label`s
   that were silently dropped before).

## Measured (local)

- Cold avg ~41 s/sheet; warm avg ~24 s (`llm_legend` ~0.1 s cached, $0).
- Docker 200–280 s was dominated by Sonnet legend RTT + failed/multi adjudicate.

No pipeline/classify/legend-rules edits. Please note in DECISIONS if useful.
Status: `coordination/status/agente-4.md`.
