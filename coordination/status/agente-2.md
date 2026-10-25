# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

M1–M4 listos. Pipeline callable; overlays y JSON de las 4 hojas en `out/`.

## Hecho

- M1 viewport + scale
- M2 legend + templates + rules
- M3 candidates + classify (fan = 1 cluster; IoU templates; codes; NMS)
- M4 `analyze_sheet` + CLI analyze + debug overlays
- Resultados: `out/plan{1..4}.json`, `out/debug/detections_p{1..4}.png`
- Mensajes a A3, A4, A5, A7, A8

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -v
uv run takeoff analyze data/plans/escondido_plans.pdf --page 0 --out out/plan1.json --debug --no-llm
```

## Siguiente

- Bajar falsos positivos (switches/receptacles) con features + adjudication
- Acelerar clustering O(n²) en planes densos (págs 3–4 ~20 s)
- Iterar mirando overlays vs ground truth de Agente 7

## Bloqueos

- Ninguno crítico. Accuracy aún no es “reviewer-ready” en todas las hojas.

## Decisions

- Wiring filter: solo cadenas *alargadas*; blobs compactos (fan/luces) se conservan.
- Ceiling fan: prior por tamaño (≥70 pt, aspect <1.35, ≥40 segs) además del template match.
- Templates degenerados (lado <2.5 pt, p.ej. FC sliver) se ignoran.
- NMS 8 pt por categoría.
- CLI analyze: Agente 2 rellena el cuerpo (overlay + counts); skeleton sigue siendo A1.

## Needs from Santiago

- (ninguno) — cuando haya ground truth de conteos, priorizar falsos de switches/luces.

## Explicación para Santiago

El motor ya recorre cada hoja de punta a punta: encuentra el plano eléctrico, lee la leyenda, junta los trazos negros en símbolos (sin paredes ni cableado punteado), los compara con los dibujos de la leyenda y les pone tipo (abanico, switch, GFI…). El abanico del dormitorio sale como **un** símbolo gracias a no borrar sus aspas como si fueran cable. La salida es un JSON por plano más un PNG con cajas de colores. Todavía hay de más en switches/tomas; eso se limpia iterando con la evaluación y, si hace falta, con Claude solo para los dudosos (nunca para las coordenadas).
