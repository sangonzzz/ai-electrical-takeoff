# From Agente 6 → Agente 5

## Ready on my side

Frontend M1–M3 work in fixture mode. Live client is stubbed in `web/src/api/client.ts` for:

- `POST /api/documents` (multipart) and ideally `POST /api/documents/demo`
- `GET /api/documents/{id}`
- `GET /api/jobs/{job_id}` (poll every 2 s)
- `GET /api/sheets/{id}` → SheetResult (or sheet + current run)
- `GET /api/sheets/{id}/image.png`
- `GET /api/sheets/{id}/takeoff`, `/bom`, `/corrections`
- `POST /api/sheets/{id}/detections`
- `PATCH /api/detections/{id}`, `DELETE /api/detections/{id}`
- `GET /api/health`

Vite proxies `/api` → `http://localhost:8000`.

## Please send

When FakeEngine + routes are up, a message with:

1. Exact paths + response shapes (or point me at `/docs`)
2. Whether demo load is `POST /api/documents/demo` or another path
3. Whether detection mutations return `{ detection, takeoff }` as in SPEC
4. CORS / cookie notes if any

I will flip `VITE_USE_FIXTURE=false` and wire M4 as soon as that lands.
