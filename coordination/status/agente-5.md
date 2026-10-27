# Agente 5 — Backend API, jobs, database

## Estado

Undo/redo API lista (restore + PATCH + `/undo` `/redo` `/history`). Mensaje a Agente 6.

## Hecho

- Upload/jobs/CRUD/BOM/exports/file_hash/document job fields
- **Undo/redo:** restore endpoint, PATCH `status` + exact fields, server undo/redo
  invirtiendo el tip del corrections log, `history` para can_undo/can_redo
- Tests en `backend/tests/test_undo_redo.py`

## Cómo probarlo

```bash
uv run pytest backend/tests/test_undo_redo.py -q
# Manual:
# POST detection → GET .../history → POST .../undo → POST .../redo
```

## Siguiente

- Agente 6 cablea `client.ts` a `/undo` `/redo` `/history` (e2e `undo_then_redo`)

## Bloqueos

- Ninguno en backend; e2e verde cuando Agente 6 consuma los endpoints

## Decisions

- Undo tip = última corrección `create|update|delete|redo`; redo tip = `undo`
- Nueva edición tras undos invalida redo (tip deja de ser `undo`)

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Para que Deshacer/Rehacer funcionen con la API real: el backend puede restaurar una
detección borrada (soft delete) y aceptar un PATCH con los valores anteriores. Además
hay `/undo` y `/redo` que invierten la última corrección y lo anotan en el log. El front
solo tiene que llamar esos endpoints y leer `/history` para habilitar los botones.
