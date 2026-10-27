# Agente 5 — Backend API, jobs, database

## Estado

E2E DB isolation (`DATABASE_URL` + migrate on startup) + fresh-analysis `reanalyze` listos.

## Hecho

- Upload/jobs/CRUD/BOM/exports/file_hash/document job fields/undo-redo
- **E2E isolation:** `AUTO_MIGRATE` (default true) → on API lifespan create DB if
  missing from `DATABASE_URL` + `alembic upgrade head`. Entrypoint also
  `ensure_database` before alembic. Point e2e at e.g. `…/takeoff_e2e`.
- **Fresh analysis:** `POST /api/sheets/{id}/reanalyze` keeps old runs; corrections
  and history scoped to `current_run_id` (empty after new run succeeds).
- Tests: `test_db_bootstrap.py`, extended `test_reanalyze_creates_new_run`

## Cómo probarlo

```bash
# Unit (no Postgres)
uv run pytest backend/tests/test_db_bootstrap.py -q

# Integration (needs Postgres)
uv run pytest backend/tests/test_detections.py::test_reanalyze_creates_new_run -q

# Isolated e2e DB (example)
DATABASE_URL=postgresql+asyncpg://takeoff:takeoff@localhost:5432/takeoff_e2e \
  uv run uvicorn app.main:app --app-dir backend --port 8000
# → creates takeoff_e2e + migrates on startup
```

## Siguiente

- Agente 6: botón “fresh analysis” → `POST /api/sheets/{id}/reanalyze`, poll job
- Agente 7: set `DATABASE_URL=…/takeoff_e2e` for e2e stack (compose override via A1)

## Bloqueos

Ninguno.

## Decisions

- Corrections/history/export log filtered by `current_run_id` so reanalyze is a
  clean slate without deleting prior correction rows.
- Admin bootstrap tries `/postgres` then `/takeoff` for CREATE DATABASE.
- Pytest sets `AUTO_MIGRATE=false` (uses `metadata.create_all`).

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Para que los e2e de Agente 7 no ensucien la base de demo, el API ahora mira
`DATABASE_URL`: si el nombre de la base no existe, la crea y corre las migraciones
al arrancar. El botón de “análisis fresco” ya tenía endpoint (`/reanalyze`); lo
ajusté para que las correcciones y el undo solo miren el run actual, así al
terminar un reanalyze la hoja queda limpia sin borrar el historial viejo.
