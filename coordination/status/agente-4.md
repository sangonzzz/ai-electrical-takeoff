# Agente 4 — AI with Claude (llm/)

## Estado

M1–M4 listos: client/cache, interpret_legend, adjudicate, baseline_vision; 22 tests offline pasan.

## Hecho

- `llm/client.py`: Anthropic wrapper, tool-use structured output, Pydantic validate + 1 retry, transport retry (429/5xx/timeout/network, backoff+jitter, max 3), `LlmUsage` tokens/cost.
- `llm/cache.py`: sha256(model, prompt_version, texts, image bytes) → `.cache/llm/`.
- `llm/legend.py` + `prompts/legend_v1.md`: merge rules↔LLM, warnings on disagreement.
- `llm/adjudicate_task.py` + `crops.py` + `prompts/adjudicate_v1.md`: crops ~300 dpi con outline, batches de 6.
- `llm/baseline.py` + `prompts/baseline_v1.md`: baseline LLM-only (eval).
- Tests con fake transport + fixtures JSON; sin red. Debug crop: `out/debug/llm_crop_cand1.png`.
- Doc: `docs/modules/ai.md`.

### Modelos / costo / cache (por sheet, estimación cold)

| Task | Modelo | ~tok in/out | ~USD |
|------|--------|-------------|------|
| interpret_legend | `claude-sonnet-5-5` | 3–6k / 1k | 0.015–0.025 |
| adjudicate (1–3 batches) | `claude-sonnet-5-5` | 8–25k / 1k | 0.02–0.07 |
| **prod LLM / sheet** | | | **~0.04–0.10** |
| baseline_vision (eval) | `claude-sonnet-5-5` | 5–15k / 2k | 0.03–0.06 |

Cache hit: 0 llamadas API, `cache_hits++`. `ANTHROPIC_MODEL_CHEAP` reservado (no usado aún en tasks de visión).

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/llm -v
```

Uso desde pipeline (opcional `usage` / `warnings`):

```python
from takeoff_engine.llm import interpret_legend, adjudicate, baseline_vision_takeoff
from takeoff_engine.models import LlmUsage

usage = LlmUsage()
warnings: list[str] = []
legend = interpret_legend(entries, legend_png, usage=usage, warnings=warnings)
adj = adjudicate(pdf_path, page_index, candidates, legend, usage=usage, warnings=warnings)
baseline = baseline_vision_takeoff(sheet_png, room_names, usage=usage, warnings=warnings)
```

Sin `ANTHROPIC_API_KEY`: rules-only + warning (engine no falla).

## Siguiente

- Grabar fixture real de Anthropic cuando Santiago ponga la key en `.env`.
- Integrar con pipeline de Agente 2 cuando legend/candidates estén listos.
- Ajustar batch size / prompts con eval de Agente 7.

## Bloqueos

- Sin `ANTHROPIC_API_KEY` en `.env` no se puede grabar respuesta real (fixtures son schema-faithful).
- Legend thumbnails dependen de `symbol_bbox` reales de Agente 2.

## Decisions

- Visión (legend, adjudicate, baseline) usa Sonnet (`ANTHROPIC_MODEL`); Haiku barato reservado.
- Kwargs opcionales `usage` / `warnings` / `client` en las 3 funciones públicas (firma requerida intacta).
- Adjudicate batch_size=6; crop pad 18 pt @ 300 dpi; outline rojo.
- Fixture legend/adjudicate/baseline hand-shaped hasta key real.

## Needs from Santiago

- `ANTHROPIC_API_KEY` en `.env` (copiar de `.env.example`) para grabar un response real en `engine/tests/llm/fixtures/`.

## Explicación para Santiago

Construí la capa de Claude: el modelo solo dice **qué** es un símbolo, nunca **dónde** está (las coordenadas las pone la geometría). Cada respuesta sale como JSON forzado por tool use, se valida con Pydantic y se guarda en caché en disco para que el demo no gaste plata dos veces. Si no hay API key, el motor sigue con reglas y avisa. Hay tres tareas: interpretar la leyenda, etiquetar candidatos dudosos con recortes de la planilla, y un baseline “solo LLM” para que en la presentación comparemos contra el híbrido. Los tests no llaman a la red; usan un transporte falso. Cuando me pases la key en `.env`, grabo una respuesta real como fixture.
