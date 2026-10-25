# Agente 4 — AI with Claude (llm/)

## Estado

M1–M4 listos + fixture real Anthropic grabado; Sonnet 5.5 client adaptado (`tool_choice: auto` + strict).

## Hecho

- Client/cache/legend/adjudicate/baseline + prompts + `docs/modules/ai.md`.
- **Sonnet 5.5 fix:** forced `tool`/`any` → 400; ahora `auto` + `strict: true` + prompt obligatorio.
- **Recording real:** Plan 1 legend → `engine/tests/llm/fixtures/legend_response.recorded.json`
  (26 entries, 6619 in / 3690 out, **$0.050**, model `claude-sonnet-5-5`).
- Segunda llamada idéntica → cache hit. Merge vs rules de Agente 2: 0 disagreements.
- `.env` con key (gitignored); `make_client` carga `.env` si falta en el entorno.
- Ack a Agente 2 (legend ready + pipeline wiring).

### Modelos / costo / cache

| Task | Modelo | Medido / estimado | USD |
|------|--------|-------------------|-----|
| interpret_legend (Plan 1, cold) | `claude-sonnet-5-5` | **6619 / 3690 tok** | **$0.050** |
| adjudicate (1–3 batches) | same | ~8–25k / 1k (est.) | ~0.02–0.07 |
| **prod LLM / sheet** | | | **~0.07–0.12** |
| baseline_vision (eval) | same | est. | ~0.03–0.06 |

Cache hit: 0 API, `cache_hits++`.

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/llm -v
```

## Siguiente

- Fixture real de `adjudicate` cuando haya candidatos `needs_review` estables del pipeline.
- Ajustar prompts con eval de Agente 7.

## Bloqueos

- Ninguno para legend. Adjudicate real recording espera crops de candidatos del pipeline.

## Decisions

- Sonnet 5.5: `tool_choice: auto` + `strict: true` (no forced tool).
- Maps como listas de pares (strict schema).
- Visión con Sonnet; Haiku reservado.
- Fixture sintético (`legend_response.json`) + recorded (`legend_response.recorded.json`).

## Needs from Santiago

- (ninguno — key recibida y usada solo en `.env` local)

## Explicación para Santiago

La key quedó solo en `.env` (no va a git). Con ella grabé una respuesta real de Claude interpretando la leyenda del Plan 1: 26 filas, ~0.05 USD. Sonnet 5.5 ya no deja forzar el tool; ajusté el cliente a `auto` + schema estricto y sigue validando con Pydantic y cache. Los tests offline siguen sin red; el fixture grabado se valida en CI sin llamar a Anthropic otra vez.
