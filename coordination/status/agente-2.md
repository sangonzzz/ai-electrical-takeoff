# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

**Disposal `$` restored** (plan 1 kitchen). Half-hot fix kept. Ask A1 to bump patch.

## Hecho

| Fix | Behavior | Commit |
|-----|----------|--------|
| R7b attic | Gray-stroke panel + circle-ring light @~(1117,436) → Attic | `e6879b0` |
| R7b disposal `$` | Seed `_switches_near_exhaust` from `afci_half_hot` as well as exhaust (R7 had removed the false sink exhaust that used to anchor recovery). Switch @~(973,353) `single_pole`. Plan 1 switch min **13**. | *(this commit)* |

### Verify

```bash
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
# switches >= 13; disposal near (975,354) single_pole; sink half-hot still afci_half_hot
uv run pytest engine/tests/symbols/ -q
```

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/test_attic_and_halfhot_r7.py engine/tests/symbols/test_category_count_regression.py -q
```

## Siguiente

- Agente 1: bump `PIPELINE_VERSION` patch + push

## Bloqueos

- Push only Agente 1.

## Decisions

- Disposal `$` recovery anchors on half-hot (correct label) with the same horizontal-stem geometry as the old exhaust-adjacent path.

## Needs from Santiago

- Confirm kitchen disposal `$` on overlay; A1 bump + push.

## Explicación para Santiago

Al corregir el tomacorriente half-hot del fregadero, perdimos el ancla que usaba el motor para encontrar el interruptor del disposal (antes el half-hot estaba mal etiquetado como exhaust). Ahora esa misma búsqueda también parte del half-hot correcto: el `$` bajo el fregadero (~975, 354) vuelve como `single_pole`, el half-hot sigue bien, y el test de plan 1 exige 13 interruptores. Pedir a Agente 1 el bump de versión.
