# Agente 7 — Evaluation, overlay, CI checks

## Estado

Golden refresheado a `eval/golden/current/`; suite completa **183 passed**.

## Hecho

- Capturé fingerprints actuales → `eval/golden/current/plan{1..4}.json`
  (`analyze_sheet`, `use_llm=False`, `with_bom=True`)
- `GOLDEN_DIR` / `test_golden.py` apuntan a `current/`
- Documenté diffs aceptados vs v0.6.4 en `eval/golden/CHANGES.md`
  (rooms/B14/merges; plan3 half-hot lost; plan4 `needs_review` flips)
- Script: `eval/scripts/capture_golden_current.py`
- Baseline histórico `eval/golden/v0.6.4/` se conserva como referencia

### Capture counts (current)

| plan | dets | rooms | wires | boxes |
|------|------|-------|-------|-------|
| 1 | 55 | 10 | 19 | 51 |
| 2 | 64 | 13 | 26 | 61 |
| 3 | 70 | 15 | 50 | 68 |
| 4 | 89 | 15 | 66 | 87 |

## Cómo probarlo

```bash
.\.venv\Scripts\python.exe eval/scripts/capture_golden_current.py
uv run pytest engine/tests/eval/test_golden.py -q
uv run pytest -q
```

Último full run: **183 passed** in 1538.68s (2026-10-27).

## Siguiente

Vigilar inbox A2/A5/A6; si se restaura el half-hot de plan3, re-capturar golden
con bump documentado en CHANGES.md.

## Bloqueos

Ninguno para la suite verde.

## Decisions

Santiago aceptó absorber room/B14 changes + plan3 half-hot loss + plan4
`needs_review` en el golden `current/` (no reescribir `v0.6.4/`).

## Needs from Santiago

Ninguno.

## Explicación para Santiago

Actualicé el golden al comportamiento del motor de hoy. Los planos 1–4 se
vuelven a analizar sin LLM, se normalizan (ids estables, floats a 0.01) y se
guardan en `eval/golden/current/`. El test de regresión compara contra eso.
Lo que cambió respecto al snapshot viejo v0.6.4 está listado en CHANGES.md:
nombres/asignaciones de cuartos (closet B14, merges), un receptáculo half-hot
que ya no se detecta en el plan 3, y tres banderas `needs_review` en el plan 4.
Esas diferencias las aceptaste como límites conocidos. Pytest completo: 183
pasados, cero fallos.
