# Agente 5 — Backend API, jobs, database

## Estado

API de edición de cables/cajas lista (bom_edit + soft-delete + reattach). Tests verdes
en DB aislada.

## Hecho

- E2E isolation / AUTO_MIGRATE / alembic path absoluto
- Undo/redo detecciones; exports Excel/PDF
- **Cable edit (esta noche):**
  - `GET/POST /api/sheets/{id}/wire-runs` (POST **201**)
  - `PATCH/DELETE /api/wire-runs/{id}` + `POST …/restore` (soft-delete)
  - Mover detección → `reattach_runs` + `compute_boxes` + BOM en la misma transacción
  - Correcciones `wire_run`; undo/redo del tip también para cables
  - Migración `003` (`wire_runs.status`); tests `test_wire_edit.py`
- Mensajes a Agente 6 y 7 con payloads finales

## Cómo probarlo

```bash
# Postgres de prueba aislado (NO la DB demo takeoff), p.ej. puerto 55432
$env:TEST_DATABASE_URL='postgresql+asyncpg://takeoff:takeoff@127.0.0.1:55432/takeoff_test'
uv run pytest -c backend/pytest.ini backend/tests/test_wire_edit.py backend/tests/test_undo_redo.py -q
```

## Siguiente

- Agente 6 cablea UI de cables al API nuevo
- Agente 7 rebuild e2e API (migración 003)

## Bloqueos

Ninguno.

## Decisions

- Soft-delete de cables en columna DB `status` (no está en el contrato WireRun)
- `cable_type` manual → `source=user` para que `bom_edit.recompute_run` lo conserve
- Runs ligados a detección borrada: se ocultan del BOM/listado; no se destruyen
- Cajas `source=user` se conservan; las de geometría se regeneran con `compute_boxes`
- Pytest: loop de asyncio `session` (`backend/pytest.ini`) por asyncpg en Windows

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Ya se pueden crear, editar, borrar (suave) y restaurar tramos de cable desde la API,
usando las funciones puras de Agente 8 (`bom_edit`) sin volver a trazar el plano ni
tocar la versión del pipeline. Si arrastras un interruptor, los cables unidos se
reenganchan y se recalculan cajas y BOM en la misma operación. Deshacer/rehacer
también entiende correcciones de cable. Los exports Excel/PDF muestran lo editado.
La base de demo no se tocó: los tests usan una Postgres aparte.
