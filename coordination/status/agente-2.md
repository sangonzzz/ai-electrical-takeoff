# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

M1 + M2 listos. Siguiente: M3 candidatos + classify.

## Hecho

- M1: viewport + scale (tests + `out/debug/viewport_p{1..4}.png`)
- M2: `extract_legend` + `legend_templates` + rule mapping SPEC §1–2
  - Plan 1 ≥25 entries (fan, recessed, switch, GFI, smoke/CO)
  - Debug: `out/debug/legend_p1.png`
  - Mensaje a Agente 4

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -v
```

## Siguiente

- M3: `find_candidates` + `classify_candidates` + overlays + conteos por página

## Bloqueos

- Ninguno (LLM interpret_legend es opcional; pipeline M4 tolerará NotImplementedError)

## Decisions

- Viewport: solo verticales negras con tramo *arriba* del título (Plan 4).
- Legend: texto de descripción **dirigido por símbolo** (banda vertical entre peers de la misma columna) para no fusionar filas; pairing below para el ceiling fan.
- Plumbing / attic / wiring: excluidos de `LegendEntry`.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Ya tenemos el recorte del plano eléctrico (viewport) y la leyenda leída fila a fila. Cada fila de la leyenda guarda el dibujito del símbolo (para compararlo después con lo del plano) y el texto (para saber si es un abanico, un switch, un GFI, etc.). No usamos la IA para coordenadas: la geometría del PDF dice dónde está cada cosa. Lo siguiente es agrupar los trazos negros dentro del viewport en “candidatos” y compararlos con esas plantillas de la leyenda.
