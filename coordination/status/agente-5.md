# Agente 5 — Backend API, jobs, database

## Estado

M1–M4 implementados (FakeEngine). Falta Postgres compose para correr tests de integración en esta máquina.

## Hecho

- Skeleton: settings, async SQLAlchemy, Alembic `001_initial_schema`, `/api/health`, CORS `localhost:5173`, OpenAPI `/docs`
- Upload `POST /api/documents` → storage + sheets + ARQ jobs (202); worker + `ENGINE=fake` FakeEngine
- Idempotencia por `file_hash` + `pipeline_version`; reanalyze versiona runs
- CRUD detections (soft delete, room auto/manual, corrections); image.png 150 dpi cacheado
- Takeoff / BOM / wire-run & box CRUD / corrections / export.csv / demo script
- Tests: unitarios OK; integración skip sin DB compose; mensaje a Agente 1 (deps) y Agente 6 (API)

## Cómo probarlo

```bash
docker compose up -d db redis
uv sync --all-packages --group dev
# Pedir a Agente 1: sqlalchemy[asyncio] / greenlet en backend/pyproject.toml
cd backend && uv run alembic upgrade head
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
# otra terminal:
uv run arq app.worker.WorkerSettings
# ENGINE=fake en .env
uv run python backend/scripts/demo_upload.py
uv run pytest backend/tests -q
```

## Siguiente

- Re-correr tests de integración cuando Docker/Postgres takeoff esté arriba
- Cambiar `ENGINE=real` cuando Agente 2 termine `analyze_sheet`
- Quitar fallback de `assign_room` cuando Agente 3 lo implemente

## Bloqueos

- Necesita `greenlet` / `sqlalchemy[asyncio]` en `backend/pyproject.toml` (pedido a Agente 1)
- Docker Desktop apagado aquí → no pude validar contra compose Postgres

## Decisions

- Job id = `analysis_runs.id` (no tabla jobs separada)
- `INLINE_JOBS=true` en tests para no depender de Redis
- Entity ids se uniquifican por run (`id__{runTag}`) para permitir reanalyze con FakeEngine
- `POST /api/documents/demo` para el botón Load demo del front (pedido Agente 6)
- BOM cableado a Agente 8; rooms.assign_room de Agente 3 (sin fallback)

## Needs from Santiago

- Arrancar Docker Desktop / `docker compose up -d` para validar el stack completo
- Confirmar con Agente 1 el cambio de dependencia greenlet

## Explicación para Santiago

El backend recibe el PDF, lo guarda por hash y crea un “trabajo” (analysis run) por cada hoja. Un worker de ARQ (cola en Redis) analiza cada hoja en un hilo: hoy usa un FakeEngine con el fixture de Plan 1 para que el front pueda integrar sin esperar al pipeline real. Los resultados (cuartos, símbolos, cables, cajas) quedan versionados por run; si subes el mismo PDF otra vez, reutiliza el run exitoso. Cuando corriges un símbolo, se recalcula el takeoff con la función pura del engine y se guarda un log before/after. Reanalizar crea un run nuevo sin borrar el anterior. Elegí ARQ porque encaja con FastAPI async y deja el CPU pesado fuera del proceso HTTP.
