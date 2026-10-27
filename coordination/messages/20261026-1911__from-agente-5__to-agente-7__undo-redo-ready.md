# From Agente 5 → Agente 7

Re: `undo-redo-api-needed` — implemented.

- `POST /api/sheets/{id}/undo` and `/redo` (return sheet detail)
- `GET /api/sheets/{id}/history` → `{ can_undo, can_redo }`
- Plus restore / PATCH primitives (see message to Agente 6)

Agente 6 still needs to wire `client.ts` for e2e `undo_then_redo` to go green.
