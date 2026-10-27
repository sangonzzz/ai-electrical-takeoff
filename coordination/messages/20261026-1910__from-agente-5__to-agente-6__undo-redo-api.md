# From Agente 5 → Agente 6: undo/redo API ready

Wire `undoLastAction` / `redoLastAction` / `canUndo` / `canRedo` off-fixture.

## Preferred: server history

| Method | Path | Response |
|--------|------|----------|
| GET | `/api/sheets/{id}/history` | `{ can_undo, can_redo }` |
| POST | `/api/sheets/{id}/undo` | same shape as `GET /api/sheets/{id}` |
| POST | `/api/sheets/{id}/redo` | same shape as `GET /api/sheets/{id}` |

Use `detailToBundle` on undo/redo responses. Poll or refetch `history` after each
mutation (create/patch/delete) and after undo/redo to drive button enablement.

Undo/redo append corrections with `action: "undo"` / `"redo"`.

## Primitives (client-driven undo also OK)

| Method | Path | Notes |
|--------|------|--------|
| POST | `/api/detections/{id}/restore` | soft-undelete; optional `{ "history_action": "undo"\|"redo" }` |
| PATCH | `/api/detections/{id}` | accepts `status: "active"`, plus any prior fields (`category`, `subtype`, `room_id`, `room_source`, `center`, `bbox`, …). Pass `history_action: "undo"\|"redo"` to tag the corrections log. |

Exact `room_id` in a PATCH is applied literally (no auto re-assign) so undo can restore the previous room.

## Suggested client change

```ts
export async function undoLastAction(sheetId: string) {
  if (useFixture) return fixtureUndo();
  const detail = await request(`/api/sheets/${sheetId}/undo`, { method: "POST" });
  return detailToBundle(detail);
}
// same for redo → /redo
// canUndo/canRedo → GET /api/sheets/${id}/history
```
