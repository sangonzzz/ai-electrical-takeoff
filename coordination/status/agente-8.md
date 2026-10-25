# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

BOM listo; fix anti-phantom wires (cobertura de dashes ≥70%) en Plan 1.

## Hecho

- Medición Plan 1: dash median **7.1 pt**, gap median **3.8 pt**
- `find_wire_runs` / `compute_boxes` / `compute_bom` + YAML precios/assumptions
- **Fix:** ya no se emiten cuerdas rectas device→device sin tinta dashed
  - Causa: al partir un chain en hops multi-device, si el bbox no encontraba puntos, se inventaba un segmento recto entre centros (p.ej. pared izq. → attic)
  - Ahora: sub-polyline por parámetro de arco entre devices; si no hay geometría de dash, se descarta el hop
  - Gate: si **>30%** de la longitud muestreada no tiene dash cerca (radio 4 pt), se rechaza el run
- Tests BOM (incl. cobertura / anti-chord)
- Docs `docs/modules/bom.md` actualizado
- Mensajes a A5/A6/A1/A2

## Cómo probarlo

```bash
.venv/Scripts/python -m pytest engine/tests/bom/ -v
.venv/Scripts/python engine/tests/bom/render_debug.py
```

## Siguiente

- Re-correr analyze Plan 1 con detections reales + ENABLE_BOM y revisar overlay
- Completar precios `verified: false` cuando Santiago los pase

## Bloqueos

- Ninguno para el fix de phantoms

## Decisions

- Waste 10% en `compute_bom`, no en `WireRun.total_length_ft`
- Encadenado por proximidad; dirección solo tie-break
- **MAX_UNCOVERED_FRACTION = 0.30** — reject runs mostly over empty plan
- Nunca emitir chord centro–centro sin puntos de dash

## Needs from Santiago

Precios aún `verified: false` (ver `data/price_list.yaml`): 3-gang box/plate, dimmers/fan switches, receptacles, fixtures.

## Explicación para Santiago

Había un cable “fantasma” en el overlay: una línea recta larga de la pared izquierda al attic que no seguía ninguna rayita dashed. Pasaba porque, al conectar varios dispositivos sobre una misma cadena, si el recorte fallaba el código inventaba un trazo recto entre los dos aparatos. Ahora solo aceptamos corridas cuya geometría viene de las rayitas del plano, y además medimos qué porcentaje del trazo tiene tinta dashed cerca: si más del 30% va por vacío, se tira. Así el BOM no cuenta metros inventados.
