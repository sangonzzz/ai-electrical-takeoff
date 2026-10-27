# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

Listo el soporte de **edición** de cables/cajas (`bom_edit.py`) sin tocar el trazado congelado v0.6.4. Mensajes enviados a Agente 5 y 6.

## Hecho

- Nuevo módulo puro `engine/takeoff_engine/bom_edit.py`:
  - `recompute_run` — pies de plano, vertical, total; tipo de cable por regla (salvo override `source=user`)
  - `reattach_runs` — al mover un detection, mueve solo la punta; devuelve solo runs cambiados
  - `make_user_run` — run manual; recto si `points is None`
- Tests: `engine/tests/bom/test_bom_edit.py` (9) — recompute, reattach, user run, gangs 2G↔1G+1G, BOM 14/2→14/3 precio
- `compute_bom` / `compute_boxes` sin cambio de firma
- **No** se tocó `find_wire_runs` / `analyze_sheet` / `PIPELINE_VERSION`
- Docs § Editing en `docs/modules/bom.md`
- Mensajes a Agente 5 (API) y Agente 6 (UI)

## Cómo probarlo

```bash
uv run --package takeoff-engine pytest engine/tests/bom/test_bom_edit.py -q
uv run --package takeoff-engine pytest engine/tests/bom/ -q
```

## Siguiente

- Agente 5: cablear PATCH move / POST wire con `reattach_runs` + `compute_boxes` + `compute_bom`
- Agente 6: UI de arrastre / tipo de cable / run manual consumiendo esa API

## Bloqueos

Ninguno (engine listo; falta wiring backend/UI).

## Decisions

- Override manual = `source == "user"` mantiene `cable_type` en `recompute_run`
- `make_user_run` sin `cable_type` infiere una vez (vía recompute temporal `geometry`) y guarda `source=user`
- Cajas siguen 100% derivadas de `compute_boxes` (no CRUD de Box)

## Needs from Santiago

Ninguno esta noche.

## Explicación para Santiago

Dejé listo el motor para que puedas **mover un switch, cambiar un cable y ver cajas, pies y precio actualizarse**, sin volver a trazar el PDF (eso sigue congelado en v0.6.4 para no romper el golden de Agente 7). Las funciones nuevas solo recalculan longitudes y tipo de cable, reenganchan las puntas cuando mueves un aparato, y crean runs manuales. Las cajas se siguen armando solas por distancia (2 gang ↔ dos de 1). Documenté el flujo y avisé a Agente 5 (API) y Agente 6 (UI) con firmas y ejemplos JSON.
