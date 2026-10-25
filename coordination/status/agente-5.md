# Agente 5 — Backend API, jobs, database

## Estado

M1–M4 + review/idempotency fixes. Pedido a Agente 1: `ENGINE=real` en compose/.env.example.

## Hecho

- Skeleton, upload/jobs, FakeEngine, CRUD, BOM, demo endpoint
- **Fix idempotency:** no sobreescribir `pipeline_version` con el label interno del pipeline;
  clave = `takeoff_engine.__version__` (`0.1.0`). Re-upload / demo reusa runs succeeded
- `max_jobs=4` en el worker ARQ
- Default settings `ENGINE=real`; tests siguen con `ENGINE=fake`
- `POST .../review-complete`, `GET .../ground-truth.json`
- Alembic `002_human_reviewed`
- Mensajes a Agentes 1, 6, 7

## Cómo probarlo

```bash
docker compose up -d db redis
cd backend && uv run alembic upgrade head
# API + worker (ENGINE=real en env / tras cambio de Agente 1 en compose)
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
uv run arq app.worker.WorkerSettings
# Dos veces el mismo demo: mismos job_id, status succeeded, sin jobs nuevos
curl -X POST http://localhost:8000/api/documents/demo
uv run pytest backend/tests -q
```

## Siguiente

- Confirmar con Agente 1 el flip `ENGINE=real` en compose
- Integración review UI (Agente 6)

## Bloqueos

- Compose aún puede tener `ENGINE=fake` hasta que Agente 1 lo cambie

## Decisions

- Job id = `analysis_runs.id`
- `pipeline_version` = package `__version__`, no `PIPELINE_VERSION` del módulo pipeline
- Idempotency también reusa runs `queued`/`running` in-flight
- Ground-truth `room` = `display_name`

## Needs from Santiago

- Ninguno urgente (Agente 1 para compose)

## Explicación para Santiago

El bug de “Load demo” que reanalizaba todo venía de que, al terminar el job, guardábamos
otra versión de pipeline (la etiqueta interna del engine) distinta a la que usamos para
buscar runs viejos. Ahora la versión es la del paquete (`0.1.0`) y no se pisa al guardar.
Así el mismo PDF + misma versión reutiliza los 4 resultados al instante. El worker puede
analizar las 4 hojas a la vez. Además hay un endpoint para marcar “revisión humana lista”
y otro para exportar las detecciones activas en el JSON que usa la evaluación.
