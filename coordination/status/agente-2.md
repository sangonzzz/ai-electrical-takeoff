# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

**Round 7 done** (last engine round). Attic light→Attic; sink half-hot by legend+geometry; viewport/legend generalization. Ask A1 to bump patch.

## Hecho

| Fix | Behavior | Commit |
|-----|----------|--------|
| R7.1–2 | Attic circle+cross light locked to Attic; sink ~975,323 → `afci_half_hot`; range yin-yang stays exhaust | `273d3e7` |
| R7.3 | Soft titles (`ELECTRICAL\|POWER\|LIGHTING PLAN`); largest-drawing viewport + warning; builtin legend + warning; Escondido unchanged | *(this commit)* |

### Plan 1 kitchen sink — legend template scores (~975, 323)

Candidate nearest the half-filled sink glyph vs Escondido legend templates (dilated IoU):

| Legend row | Subtype | IoU (best rot) |
|------------|---------|----------------|
| DUPLEX OUTLET AFCI-HALF HOT | `afci_half_hot` | **0.88** (90°) on compact duplex @~(973,295); geometry fill path emits `afci_half_hot` @~(975.4,322.8) |
| EXHAUST FAN | `bath_exhaust` | 0.65 (180°) on same compact glyph |

**Decision:** label `afci_half_hot` (better match + thin/rotated half-fill prior). Range yin-yang @~(990,420) remains `bath_exhaust`.

### Attic

- Light @~(1120.3, 408.6) `recessed`, room display **Attic**
- `$` switch also in Attic (from R6)

### Generalization probe (`eval/scripts/generalization_probe.py`)

| Plan | Before | After |
|------|--------|-------|
| longview p4 | `ValueError` title | **ok** title=`ELECTRICAL PLAN EXAMPLE`, 14 dets, legend builtin warn |
| pbg p0 | `ValueError` title | **ok** title=`VIEWPORT_FALLBACK`, 2 dets, viewport+legend+scale warns |
| pbg p1 | `ValueError` title | **ok** title=`1ST FLOOR POWER PLAN`, 0 dets, legend builtin warn |

Escondido: no fallback warnings; `engine/tests/symbols/` 29 passed.

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
uv run python eval/scripts/generalization_probe.py
```

## Siguiente

- Agente 1: bump `PIPELINE_VERSION` patch + push
- Residual: Plan 4 Bath-2 wall vanity light

## Bloqueos

- Push only Agente 1.

## Decisions

- Soft title ≥14 pt need not be bold; Escondido still requires bold ≥18 for rank-0.
- Missing LEGEND → builtin catalog (empty geometry) so classify heuristics can run.
- Sink: geometry half-fill prior + higher half-hot IoU beats exhaust.

## Needs from Santiago

- Confirm R7 overlays / probe; A1 bump + push when ready.

## Explicación para Santiago

En la última ronda del motor: la luz del panel IN ATTIC ya se detecta y queda en la habitación Attic. En la cocina del plan 1, el símbolo medio relleno junto al disposal es half-hot (mejor score contra la leyenda AFCI-HALF HOT que contra exhaust); el yin-yang del range sigue siendo exhaust. Además, si un plano no tiene el título exacto de Escondido, el motor busca ELECTRICAL/POWER/LIGHTING PLAN o usa la región de dibujo más grande con un warning; si no hay LEGEND, usa plantillas built-in y avisa. La sonda de generalización de Agente 7 ya no truena: Longview y Palm Beach Gardens terminan con un SheetResult. Hay que pedir a Agente 1 que suba el patch de versión.
