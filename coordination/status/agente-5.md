# Agente 5 — Backend API, jobs, database

## Estado

Bug de respuesta stale en cable-edit corregido: PATCH move / wire CRUD
devuelven boxes+BOM frescos (igual que un GET).

## Hecho

- E2E isolation / AUTO_MIGRATE / alembic path / cable edit API
- **Fix stale PATCH response:** `load_fresh_entities` hace `session.refresh` de
  collections del run tras flush/commit (`expire_on_commit=False` dejaba
  `boxes`/`wire_runs` viejos en el identity map). `_finish_detection_mutation`
  y rutas wire POST/PATCH/DELETE/restore usan eso antes de armar el JSON.
- Test `test_move_patch_response_matches_subsequent_get` (2G → move → response == GET)

## Cómo probarlo

```bash
$env:TEST_DATABASE_URL='postgresql+asyncpg://takeoff:takeoff@127.0.0.1:55432/takeoff_test'
uv run pytest -c backend/pytest.ini backend/tests/test_wire_edit.py -q
```

## Siguiente

- Agente 6 / 7: rebuild API si hace falta y re-probar UI de mover switches

## Bloqueos

Ninguno.

## Decisions

- No usar `expire_all()` (expira `sheet` y dispara lazy sync → MissingGreenlet).
  Solo `refresh` de relationships del `AnalysisRun`.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Al mover un switch, la base ya quedaba bien (GET mostraba dos cajas 1G y el BOM
nuevo), pero la respuesta del PATCH seguía mandando la caja 2G vieja: SQLAlchemy
con `expire_on_commit=False` reutilizaba la lista de boxes en memoria. Ahora
recargamos detections/wires/boxes desde Postgres después del flush/commit y
calculamos boxes+BOM con eso, igual que un GET. Lo mismo en create/patch/delete/
restore de cables.
