# Agente 5 — Backend API, jobs, database

## Estado

API lista; integridad del PDF original demostrada (sha256 + docs + hash en API).

## Hecho

- Upload/jobs/CRUD/BOM/review + job fields en GET document
- Idempotency, `ENGINE=real`, `max_jobs=4`
- **PDF integrity:** store bytes unchanged; worker verifies sha256; `file_hash` en document/sheet API;
  test vs `escondido_plans.pdf`; docs confirman vectors del PDF original / PNG solo render
- Mensaje a Agente 6 para mostrar hash corto en el header

## Cómo probarlo

```bash
docker compose up -d db redis
cd backend && uv run alembic upgrade head
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
uv run pytest backend/tests/test_pdf_integrity.py backend/tests/test_unit_engine_rooms.py -q
```

## Siguiente

- Agente 6: UI del hash corto

## Bloqueos

- Ninguno

## Decisions

- Content-addressed path `storage/documents/{sha256}.pdf`; never rewrite with PyMuPDF save
- Worker fails the job if on-disk hash ≠ `documents.file_hash`

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

El PDF que subes se guarda tal cual (mismos bytes, mismo SHA-256). El análisis y la imagen
del plano abren ese archivo; la PNG es solo un render del viewport, no un PDF nuevo. En la
API verás `file_hash` en el documento y en cada hoja para comprobarlo.
