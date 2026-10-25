# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

Precision pass (fixes 1–8) listo. Conteos clave alineados con revisión visual de Santiago.

## Hecho

- M1–M4 (viewport, legend, candidates/classify, pipeline + overlays)
- Fix 1: strip dashed wiring **before** clustering (protect continuous glyphs)
- Fix 2: switches/receptacles within ~8 pt of wall mask; switch `$` IoU gate
- Fix 3: circle-in-square → recessed light (VP / wall tick refine subtype)
- Fix 4: exclude keynote tags `^[A-Z]\d{2}$`
- Fix 5: drop porch X markers; exhaust requires black half-fill
- Fix 6: ceiling fan = `J` hub + four blades (no door/cabinet fans)
- Fix 7: smoke / smoke_co need SD or SD/MA (+ orphan SD inside fan bbox)
- Fix 8: per-page counts vs expected; docs + mensaje a A7

### Conteos actuales (`--no-llm --no-bom`)

| plan | sw | fan | light | rec | smoke | smoke_co | exhaust |
|------|----|-----|-------|-----|-------|----------|---------|
| 1 | 11 | 1 | 10 | 26 | 1 | 1 | 1 |
| 2 | 10 | 2 | 15 | 32 | 2 | 1 | 3 |
| 3 | 12 | 2 | 14 | 29 | 0 | 2 | 2 |
| 4 | 15 | 3 | 14 | 38 | 1 | 1 | 2 |

Esperado visual: plan1 ~11 sw, 1 fan, smoke 1 + smoke_co 1; plan4 3 fans → **cumplido**.

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -v
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
# pages 1..4; overlays in out/debug/detections_p{1..4}.png
```

## Siguiente

- Seguir bajando receptacles falsos si eval lo pide
- Acelerar clustering O(n²) en planes densos

## Bloqueos

- Ninguno. Listo para que Agente 7 re-corra eval.

## Decisions

- Dashes: gap 1.2–6 pt chains; continuous strokes (gap &lt;1.2) never join a wire chain.
- Switch: wall ≤8 pt + `$` IoU ≥0.45 (not every near-wall mark).
- Fan hub `J`: ≤8 pt of center **or** middle third of bbox (merged clusters offset the geometric center).
- Detectors: no template-only smoke; require SD/SD/MA; orphan SD near fan still emits.
- NMS 8 pt por categoría.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Antes el cableado punteado se mezclaba con los símbolos y salían “switches” por toda la curva (~34 en el plan 1). Ahora quitamos esos guiones **antes** de agrupar, pedimos que interruptor/toma estén pegados a la pared y que el switch se parezca de verdad al `$` de la leyenda. Las luces empotradas (círculo en cuadrado) se fuerzan a light; las etiquetas A01/B14 ya no son detectores; el abanico exige la J y las aspas; el humo exige SD o SD/MA (aunque el SD esté dibujado dentro del abanico). Con eso el plan 1 da ~11 switches, 1 abanico y 1+1 detectores, y el plan 4 da 3 abanicos. Pedí a Agente 7 que vuelva a correr la evaluación.
