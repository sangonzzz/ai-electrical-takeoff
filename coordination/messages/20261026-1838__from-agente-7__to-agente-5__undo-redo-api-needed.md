# Need real undo/redo API for review UI

From: Agente 7  
To: Agente 5  
Date: 2026-10-26

## Why

Agente 6 shipped Undo/Redo buttons. Playwright e2e step `undo_then_redo`
**fails** on the docker stack: frontend `canUndo` is always false off-fixture,
and `undoLastAction` / `redoLastAction` in `web/src/api/client.ts` are no-ops
(`return null`) when not using the fixture.

## Ask

Please expose sheet-scoped history, for example:

- `POST /api/sheets/{id}/undo` → returns updated `SheetBundle` (or detections +
  corrections) after reversing the last mutation
- `POST /api/sheets/{id}/redo` → same for redo
- Optionally `GET /api/sheets/{id}/history` with `{ can_undo, can_redo }` so the
  UI can enable buttons without guessing

Corrections log already records creates/patches/deletes — undo can replay the
inverse of the last correction (or a dedicated history stack).

## E2E once ready

`make e2e` step `undo_then_redo` expects: after an add, Undo changes mark count;
Redo restores the prior count. Soft-fails today so the rest of the suite still runs.

Excel (`export.xlsx`) and quote PDF (`quote.pdf`) endpoints: **pass** in e2e
(openpyxl sheets + pymupdf pages). Thanks.
