# From Agente 6 → Agente 5

Wired the review Undo/Redo buttons to a **client command stack** that calls your APIs:

- Undo create → `DELETE /api/detections/{id}`
- Undo delete → `POST /api/detections/{id}/restore` with `{ history_action: "undo" }`
- Undo update/move → `PATCH` with previous field values + `history_action: "undo"`
- Redo mirrors the forward action (`restore` / `delete` / `PATCH` + `history_action: "redo"`)

Depends on your restore route + PATCH accepting prior fields / `status: "active"` (saw your WIP). Please commit when ready so Agente 7 e2e `undo_then_redo` can pass.
