# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

Round 5 listo: recessed downlights son geometría (no score). Overlays 1–4 revisados.

## Hecho

### Round 5

| Cambio | Qué |
|--------|-----|
| Geometric recessed | Círculo r≈3.5–4.5 pt en cuadrado ~8–12 pt; exclusiones R4 (hub J, gray, footprint) |
| Viewport ring scan | Recupera cans sin candidate propio (plan 2 attic) |
| Footprint | Nunca dropea fans/detectors/exhaust (Bed 2 fan plan 3) |
| Regression | Mínimos plan1–4 luces/fans; plan4 luces 13–17; switches sin bajar |

### Counts R5 (`--no-llm --no-bom`)

| plan | light | fan | switch |
|------|-------|-----|--------|
| 1 | 10 | 1 | 12 |
| 2 | 13 | 2 | 10 |
| 3 | 17 | 2 | 11 |
| 4 | 16 | 3 | 15 |

(R4 había dejado luces en 8/8/6/13.)

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 3 --out out/plan3.json --debug --no-llm --no-bom
# overlays: out/debug/detections_p{1..4}.png
```

## Siguiente

- Agente 1: bump patch + push R4–R5
- Agente 7: re-eval

## Bloqueos

- Push solo Agente 1.

## Decisions

- Recessed = geometría determinista, no umbral de IoU de leyenda.
- Wall vanity: score ≥0.55, o aspect≥1.9 con score≥0.30 (plan 1 bath).
- Tall weak wall-tick + recessed ring → drop (plan 4 false); wide merge → recessed (plan 2 kitchen).

## Needs from Santiago

- Agente 1 bump patch (mensaje enviado).

## Explicación para Santiago

En el round 4 se cortaron demasiadas luces (sobre todo planes 2 y 3). Ahora un downlight recessed se reconoce por forma: círculo de radio ~4 pt dentro de un cuadrado de ~8–12 pt, sin exigir un score alto de la leyenda. Seguimos excluyendo el hub J de los abanicos, gabinetes grises y basura fuera del edificio. El abanico de Bed 2 en el plan 3 vuelve a salir. Un test de regresión fija mínimos por plan para que no se vuelva a vaciar ni a duplicar en silencio.
