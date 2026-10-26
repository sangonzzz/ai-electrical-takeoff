# Agente 4 — AI with Claude (llm/)

## Estado

LLM latency profiled + optimized (Haiku legend, 1 adjudicate call/sheet, disk cache actually hits).

## Hecho

### Measurement (local, Escondido, `with_bom=False`)

**Before (Sonnet legend, batch=6, cache broken by uuid4 in prompts):**

| Sheet | wall | llm_legend | llm_adjudicate | calls | USD |
|-------|------|------------|----------------|-------|-----|
| p0 | ~34–64 s | ~19–54 s | — (0 needs_review) | 1 | ~0.05 |
| p1 | ~33 s | ~21 s | — | 1 | ~0.05 |
| p2 | ~58 s | ~23 s | ~1.4 s (API **failing**) | 1 | ~0.05 |
| p3 | ~61 s | ~19 s | — | 1 | ~0.05 |

Bottleneck: **`llm_legend` ≈ 20–25 s/sheet** (Sonnet). Adjudicate rarely needed (0–2 classify `needs_review`); when it ran it **400’d** on strict schema (`minimum`/`maximum` on `confidence`). Docker 200–280 s/sheet was mostly API RTT × N + Sonnet legend (geometry also heavy on p2/p3).

**After (Haiku legend, one adjudicate batch, stable cache ids, schema transform):**

| | cold avg/sheet | warm avg/sheet | cold calls (4 sheets) | warm calls | cold USD | warm USD |
|--|----------------|----------------|----------------------|------------|----------|----------|
| **Measured** | **40.6 s** | **23.9 s** | 5 | **0** | **$0.024** | **$0** |

Per-sheet warm: `llm_legend` **~100–130 ms** (cache hit). Warm p2 `llm_adjudicate` ~0.8 s = crop render only (API cached).

Haiku vs Sonnet legend (Plan 1): **0 category/subtype diffs** (also 0 vs rules).

### Code changes (llm/ only — no detection rules)

1. `interpret_legend` → `ANTHROPIC_MODEL_CHEAP` (Haiku).
2. `DEFAULT_BATCH_SIZE = 10_000` → one adjudicate API call per sheet.
3. Stable content ids in prompts (`llm/ids.py`) so `.cache/llm` hits across uuid4 remints.
4. `anthropic.transform_schema` so Sonnet 5.5 accepts adjudicate tool schema.
5. Batch crop render (one PDF open); latency logged per call.

## Cómo probarlo

```bash
uv run pytest engine/tests/llm -q
# cold then warm (second run should show cache_hits, llm_legend ~100ms):
uv run python -c "from pathlib import Path; from takeoff_engine.pipeline import analyze_sheet; r=analyze_sheet(Path('data/plans/escondido_plans.pdf'),0); print(r.timings_ms, r.llm_usage)"
```

## Siguiente

- Ask Agente 2 for stable legend/detection ids (optional; we already hash content).
- Geometry time on p2/p3 (candidates/classify 20–40 s) is outside A4.

## Bloqueos

- Ninguno.

## Decisions

- Legend = Haiku after accuracy parity check.
- One adjudicate call/sheet.
- Cache keys ignore pipeline uuid4 via stable content ids.

## Needs from Santiago

- **FYI before/with this commit:** Adjudicate was silently failing (400 schema). Fix restores labeling on sheets with `needs_review` (Plan 3 / page 2 got 1 `llm_label` in measurement). Haiku legend matched Sonnet on Plan 1 — no taxonomy change expected from the model swap. Detection rules untouched.

## Explicación para Santiago

Medí los tiempos: casi todo el LLM era la leyenda con Sonnet (~20 s y ~0.05 USD por hoja). Pasé la leyenda a Haiku (misma precisión en el Plan 1) y arreglé la caché (antes nunca pegaba porque cada run inventaba UUIDs nuevos). La segunda corrida deja la leyenda en ~0.1 s y 0 USD. También unifiqué la adjudicación a **una sola** llamada por hoja y arreglé un bug que hacía fallar adjudicación en la API. En caliente, lo lento que queda en las hojas 3–4 es geometría (candidates/classify), no Claude.
