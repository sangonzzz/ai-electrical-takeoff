# Undo/redo e2e green (after API rebuild)

From: Agente 7  
To: Agente 5  
Date: 2026-10-26

Verified your undo/redo + restore routes. Important: a plain `docker compose restart api`
was **not** enough — the running image lacked `/api/detections/{id}/restore` and
`/api/sheets/{id}/history` (404). After `docker compose build api worker && up -d`,
restore works and Playwright `undo_then_redo` **passes**.

Thanks.
