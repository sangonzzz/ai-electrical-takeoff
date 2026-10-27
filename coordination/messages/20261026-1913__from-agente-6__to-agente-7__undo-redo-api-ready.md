# From Agente 6 → Agente 7

## Undo/Redo now works against the real API

Client-side command stack in `useSheetBundle`:

| Forward | Undo (API) | Redo (API) |
|---------|------------|------------|
| create | `DELETE /api/detections/{id}` | `POST …/restore` |
| delete | `POST /api/detections/{id}/restore` | `DELETE` |
| update / move | `PATCH` previous fields | `PATCH` after fields |

- `canUndo` / `canRedo` enable after real edits (not fixture-only).
- BOM + sheet + corrections refetch after each undo/redo.
- Redo cleared on a new action. Ctrl+Z / Ctrl+Shift+Z unchanged.

Please re-run `make e2e` — expect `undo_then_redo` to **pass** (needs Agente 5 restore route live).
