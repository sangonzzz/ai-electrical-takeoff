# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

Wires **v2** shipped: full-curve growth, bbox ends, fixture splits, `nm_14_3` travelers. Awaiting Agente 1 version bump.

## Hecho

- Rebuilt `find_wire_runs` (v2):
  1. Collect dashes (1.5–14 pt)
  2. Greedy curve growth: gap ≤ typical_max×2 (9 pt; ~12 if aligned) + tangent continuity
  3. Tip → nearest **bbox boundary** (prefer 3-way / switch)
  4. Mid-path fixture splits; farthest distant 3-way pair on a curve → `nm_14_3`
  5. No dashless runs (uncovered gate)
- Debug PNGs with teal dash underlay + labeled pink/green runs
- Tests, `docs/modules/bom.md`, `assumptions.yaml` updated
- Message to Agente 1 (Santiago-approved engine change)

## Run counts (v2)

| Plan | runs | nm_14_2 (n / ft) | nm_14_3 (n / ft) |
|------|------|------------------|------------------|
| 1    | 42   | 41 / 549.9       | 1 / 34.4         |
| 2    | 48   | 48 / 598.5       | 0 / 0.0*         |
| 3    | 58   | 58 / 848.2       | 0 / 0.0          |
| 4    | 75   | 74 / 1059.4      | 1 / 36.1         |
| **Σ**| **223** | **/ 3055.9**  | **/ 70.5**       |

\*Plan 2: only co-located 3Ds (same gang) — no traveler on the drawing.

## Cómo probarlo

```bash
.venv/Scripts/python -m pytest engine/tests/bom/test_wires.py -v
.venv/Scripts/python engine/tests/bom/render_debug.py
```

PNGs: `out/debug/wires_plan{1..4}.png`

## Siguiente

- Reviewer feedback on PNG coverage
- Unverified prices

## Bloqueos

- Agente 1: bump `PIPELINE_VERSION` (freeze §14; Santiago approved wires v2)

## Decisions

- Gap ×2 from typical-max 4.5 → 9.0; aligned tips to ~12
- Mid-path split 8 pt; 3-ways use tip radius (22) so mid-curve travelers register
- Traveler = max-separation 3-way pair on a curve (≥25 pt), not first/last path order

## Needs from Santiago

None for wires. Prices still `verified: false` in places.

## Explicación para Santiago

Reescribí detección de cables (v2). Ahora armo **curvas completas** uniendo rayitas dashed (distancia entre puntas ≤ gap×2 y misma dirección), corto en cada aparato que toca la curva, y el extremo se pega al **borde del símbolo**. Si en una curva hay dos 3-way lejos (laundry↔entrada), esa corrida es `nm_14_3`. Los PNG en `out/debug/` muestran las rayitas de fondo y encima cada corrida con tipo y pies.
