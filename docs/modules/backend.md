# Backend module (Agente 5)

FastAPI API + ARQ worker + SQLAlchemy/Alembic persistence for electrical takeoff.

## What it does

- Accepts a multi-page PDF, stores it under `storage/documents/{sha256}.pdf`.
- Creates one `sheets` row per page and one `analysis_runs` job per sheet.
- Worker runs `takeoff_engine.pipeline.analyze_sheet` (or `FakeEngine` when `ENGINE=fake`) in a thread.
- Persists rooms, legend, detections, wire runs, and boxes for that run.
- Serves sheet data, viewport PNG (PyMuPDF @ 150 dpi, disk-cached), takeoff, BOM, CRUD, corrections, CSV export.
- **Never** recomputes counts in the API: always `takeoff_engine.takeoff.compute_takeoff` and Agente 8 `compute_bom`.

## Data model

| Table | Role |
|-------|------|
| `documents` | PDF metadata + content hash |
| `sheets` | One page; `current_run_id` points at the live analysis |
| `analysis_runs` | Job + versioned result (`pipeline_version`, `schema_version`, model, timings, llm_usage, status) |
| `rooms`, `legend_entries`, `detections`, `wire_runs`, `boxes` | Belong to a run (not directly to the sheet) |
| `corrections` | Append-only before/after JSON log |

Job id == `analysis_runs.id`. Status: `queued` → `running` → `succeeded` | `failed`.

## Job flow

1. `POST /api/documents` stores the PDF, creates sheets + queued runs, enqueues ARQ `analyze_sheet_job` per run (or runs inline when `INLINE_JOBS=true`).
2. Worker sets status `running`, calls the engine in `asyncio.to_thread`, uniquifies entity ids for the run, writes child rows, sets `succeeded`, updates `sheet.current_run_id`.
3. Frontend polls `GET /api/jobs/{job_id}` and then loads `GET /api/sheets/{id}`.

### Why ARQ

ARQ is an asyncio-native Redis queue that fits FastAPI’s event loop. Analysis is CPU-bound (PyMuPDF / geometry), so the worker offloads it to a thread while keeping DB I/O async. Retries and durable job ids live in Redis; run status and results live in Postgres (source of truth).

## Idempotency

Same file SHA-256 returns the **same document**. For each page, if a `succeeded` run already exists for `(file_hash, page_index, pipeline_version)`, that run is reused and **not** re-enqueued.

## Versioning

`POST /api/sheets/{id}/reanalyze` creates a **new** run. Old runs and their corrections stay untouched. `current_run_id` switches only when the new run succeeds.

## CRUD rules

- Soft-delete detections (`status=deleted`).
- Move with `room_source=auto` → `rooms.assign_room` (fallback point-in-polygon until Agente 3 lands).
- Manual room → `room_source=manual`.
- Every create/update/delete appends a `corrections` row in the same transaction; response includes recomputed takeoff (and BOM for wire/box mutations).

## Feature flags / settings

| Env | Default | Meaning |
|-----|---------|---------|
| `ENGINE` | `real` | `real` = pipeline; `fake` = fixture (tests only) |
| `pipeline_version` | `takeoff_engine.__version__` | Idempotency key stored on each run |
| `ENABLE_LLM` / `ENABLE_BOM` | true | Passed through to the engine / BOM gate |
| `INLINE_JOBS` | false | Run worker in-process (tests) |
| `DATABASE_URL` / `REDIS_URL` | compose defaults | Postgres + Redis |

Human review: `POST /api/sheets/{id}/review-complete` sets `human_reviewed` on the
current run; `GET /api/sheets/{id}/ground-truth.json` exports active detections for
Agente 7 (`planN.detections.json`).

## How to run

```bash
docker compose up -d db redis
cd backend && uv run alembic upgrade head
# API (from repo root after uv sync):
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
# Worker:
uv run arq app.worker.WorkerSettings
# Demo upload:
uv run python backend/scripts/demo_upload.py
```

OpenAPI: `http://localhost:8000/docs`.

## Known limits

- Integration tests need compose Postgres (`takeoff` / `takeoff_test`); they skip if DB is unreachable.
- BOM returns a stub until Agente 8 implements `compute_bom` / price files.
- `FakeEngine` repeats Plan-1 fixture geometry for every page (ids suffixed per page/run).
