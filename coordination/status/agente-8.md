# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

Wires restaurados: `analyze_sheet(page0, with_bom=True)` vuelve a devolver corridas; phantoms rectos sin dash siguen rechazados.

## Hecho

- BOM completo (wires/boxes/pricing/bom) + precios Home Depot verificados donde se pudo
- **Fix anti-zero-runs:** el gate de cobertura anterior rechazaba todo / el snap de 10 pt no asociaba devices reales
  - Asociación por proximidad al polyline (`WIRE_PATH_ASSOCIATE_PT=28`) + enrich de extremos (`32`)
  - Phantom gate solo si nearly-straight (chord/len ≥ 0.90) **y** >30% sin dash
  - Snap stubs acotados (`MAX_SNAP_STUB_PT=18`); sin fallback a chain completa en hops
  - Cap `MAX_PLAN_LENGTH_FT=40`
- Debug PNGs: `out/debug/wires_plan{1..4}.png`
- Test: Plan 1 `>10` runs y ninguna `total_length_ft > 40`

## Run counts (recompute actual)

| Plan | wire_runs |
|------|-----------|
| 1    | 12        |
| 2    | 16        |
| 3    | 26        |
| 4    | 28        |

`analyze_sheet(..., page_index=0, with_bom=True)` → **12** runs.

## Cómo probarlo

```bash
.venv/Scripts/python -m pytest engine/tests/bom/ -v
.venv/Scripts/python engine/tests/bom/render_debug.py
.venv/Scripts/python -c "from takeoff_engine.pipeline import analyze_sheet; r=analyze_sheet('data/plans/escondido_plans.pdf',0,use_llm=False,with_bom=True); print(len(r.wire_runs))"
```

## Siguiente

- Mejorar recall de arcs largos (living multi-light) sin reintroducir chords
- Completar precios `verified: false`

## Bloqueos

- Ninguno

## Decisions

- Path associate 28 / end 32 (centers of symbols sit off the stroke; WIRE_SNAP_PT=10 alone → 0 runs)
- Reject phantoms only when straight **and** uncovered; curved dash paths always kept
- Never emit bare center–center chords; never use full-chain geometry for a multi-device hop fallback

## Needs from Santiago

Precios aún `verified: false` en `data/price_list.yaml` (3-gang, dimmers, receptacles, fixtures).

## Explicación para Santiago

El filtro “tiene que haber rayitas debajo” estaba demasiado agresivo y, junto con un radio de snap chico, dejaba **cero** cables. Lo aflojé: ahora cada curva dashed busca los aparatos que toca (con un margen realista) y arma corridas entre ellos. Solo tiro las líneas rectas inventadas que cruzan el plano vacío (como pared→attic). En el Plan 1 vuelven a salir más de 10 corridas y ninguna de más de 40 ft; hay PNGs de los 4 planos en `out/debug/`.
