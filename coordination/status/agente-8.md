# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

`nm_14_3` restaurado: traveler entre gangs de 3-way (códigos `3`/`3D` o subtypes); Plan 1 ≥1.

## Hecho

- BOM completo (wires/boxes/pricing/bom) + precios Home Depot verificados donde se pudo
- Wire restore: path associate 28/32, phantom gate solo recto+sin dash, cap 40 ft plan
- **`nm_14_3` traveler pass:**
  - `_is_three_way` por subtype **o** legend codes `3` / `3D` (Agente 2 deja subtype=dimmer/single_pole)
  - Cluster gangs (<40 pt); BFS en grafo de dashes entre gangs distantes
  - Ventana traveler más laxa (1.5–14 pt / gap 0.5–10) para curvas aplanadas; chain principal sigue 3–12 / 1–6
- Tests: Plan 1 `>10` runs / ninguna `>40` ft total; **≥1 `nm_14_3`**; synthetic codes `3D`
- Debug PNGs: `out/debug/wires_plan{1..4}.png`

## Run counts (recompute actual)

| Plan | wire_runs | nm_14_2 | nm_14_3 |
|------|-----------|---------|---------|
| 1    | 13        | 12      | 1       |
| 2    | 18        | 18      | 0       |
| 3    | 36        | 33      | 3       |
| 4    | 45        | 43      | 2       |

## Cómo probarlo

```bash
.venv/Scripts/python -m pytest engine/tests/bom/test_wires.py -v
.venv/Scripts/python engine/tests/bom/render_debug.py
.venv/Scripts/python -c "from takeoff_engine.pipeline import analyze_sheet; r=analyze_sheet('data/plans/escondido_plans.pdf',0,use_llm=False,with_bom=True); print(sum(1 for w in r.wire_runs if w.cable_type=='nm_14_3'), len(r.wire_runs))"
```

## Siguiente

- Plan 2: dos 3-ways detectados pero sin path dashed → investigar si el plano realmente dibuja traveler
- Completar precios `verified: false`

## Bloqueos

- Pedir a Agente 1 bump de `PIPELINE_VERSION` (patch)

## Decisions

- Codes `3`/`3D` cuentan como three-way (detectors no siempre setean subtype)
- Traveler graph separado (más corto / gaps más largos) para no inflar corridas nm_14_2
- Un traveler por par de gangs (no producto cartesiano de switches multi-gang)

## Needs from Santiago

Precios aún `verified: false` en `data/price_list.yaml` (3-gang, dimmers, receptacles, fixtures).

## Explicación para Santiago

Los 3-way en los planos suelen venir etiquetados `3D` pero el clasificador los deja como dimmer o single-pole, y el cable entre dos 3-way es 14/3 (tres conductores: hot + viajeros). Ahora miro el código de la leyenda y busco la rayita dashed que une dos cajas de 3-way lejanas (laundry↔entrada, hallway↔living). Si las encuentro, esa corrida sale como `nm_14_3`. En el Plan 1 hay al menos una; en el Plan 4 hay dos. El resto de cables sigue siendo `nm_14_2`.
