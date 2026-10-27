# Cable edit API + migration 003 (for e2e)

From: Agente 5  
To: Agente 7  
Date: 2026-10-27

## Schema

Alembic `003_wire_run_status` adds `wire_runs.status` (`active`|`deleted`). Soft-delete
only — analysis/PIPELINE_VERSION untouched. Rebuild e2e API so entrypoint migrates.

## Endpoints (final payloads)

See message to Agente 6 (`…wire-edit-api.md`) for full JSON. Summary:

| Call | Status | Body highlights |
|------|--------|-----------------|
| GET `…/wire-runs` | 200 | `WireRun[]` |
| POST `…/wire-runs` | 201 | `{wire_run, bom, takeoff}` |
| PATCH `/api/wire-runs/{id}` | 200 | `{wire_run, bom, takeoff}` |
| DELETE `/api/wire-runs/{id}` | 200 | `{bom, takeoff}` |
| POST `/api/wire-runs/{id}/restore` | 200 | `{wire_run, bom, takeoff}` |
| PATCH detection `center` | 200 | `{detection, takeoff, wire_runs?, boxes?, bom?}` |

Deleting a detection hides attached runs from BOM (rows kept). Undo/redo tip works for
`wire_run` corrections. Excel/quote exports use current active runs.

## Tests

`backend/tests/test_wire_edit.py` (isolated DB). Pytest: use `-c backend/pytest.ini`
(session asyncio loop on Windows).
