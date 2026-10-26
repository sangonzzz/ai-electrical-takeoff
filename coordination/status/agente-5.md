# Agente 5 — Backend API, jobs, database

## Estado

API lista; fix “Queued forever” en GET document (job_id + status por hoja).

## Hecho

- Skeleton, upload/jobs, FakeEngine, CRUD, BOM, demo, review/ground-truth
- Idempotency + `pipeline_version` = package version; `max_jobs=4`; `ENGINE=real` default
- **Fix Queued forever:** `GET /api/documents/{id}` sheets ahora incluyen `job_id`, `status`, `error`
- Mensaje a Agente 6 con los campos nuevos

## Cómo probarlo

```bash
docker compose up -d db redis
cd backend && uv run alembic upgrade head
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
uv run arq app.worker.WorkerSettings
curl -X POST http://localhost:8000/api/documents/demo
# Luego GET /api/documents/{id} → cada sheet trae job_id + status
uv run pytest backend/tests -q
```

## Siguiente

- Nada bloqueante; Agente 6 puede polllear document detail para status de cards

## Bloqueos

- Ninguno

## Decisions

- `job_id` = run actual (`current_run_id`) / latest run de la hoja
- `error` solo si `status=failed`

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

El front se quedaba en “Queued” porque al refrescar el documento la API no devolvía
el `job_id` ni el `status` de cada hoja; el cliente perdía los ids y no podía actualizar
las tarjetas. Ahora cada hoja en `GET /api/documents/{id}` trae `job_id`, `status` y
`error` (si falló), igual que al subir, así el polling sigue funcionando.
