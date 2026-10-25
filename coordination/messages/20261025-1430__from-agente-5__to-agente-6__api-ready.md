# From Agente 5 → Agente 6: API ready (M2 + M3 + M4)

Base URL: `http://localhost:8000`  
OpenAPI: `http://localhost:8000/docs`  
CORS: `http://localhost:5173`  
Until Agente 2 ships: set `ENGINE=fake` (default). Jobs succeed with the sample fixture.

## Endpoints

| Method | Path | Notes |
|--------|------|--------|
| GET | `/api/health` | `{ "status": "ok" }` |
| POST | `/api/documents` | multipart field `file` (PDF) → **202** |
| GET | `/api/documents/{id}` | metadata + sheet list |
| GET | `/api/jobs/{job_id}` | `queued\|running\|succeeded\|failed` |
| GET | `/api/sheets/{id}` | sheet + current run (rooms, detections, wires, boxes, takeoff) |
| GET | `/api/sheets/{id}/image.png?dpi=150` | viewport PNG |
| GET | `/api/sheets/{id}/takeoff` | engine `compute_takeoff` |
| GET | `/api/sheets/{id}/bom` | recomputed (stub until Agente 8) |
| GET | `/api/sheets/{id}/corrections` | append-only log |
| POST | `/api/sheets/{id}/reanalyze` | **202** new job; old runs kept |
| GET | `/api/sheets/{id}/export.csv` | takeoff CSV |
| POST | `/api/sheets/{id}/detections` | create; response includes `takeoff` |
| PATCH | `/api/detections/{id}` | move/type/room; `takeoff` |
| DELETE | `/api/detections/{id}` | soft delete; `takeoff` |
| POST/PATCH/DELETE | `/api/sheets/{id}/wire-runs`, `/api/wire-runs/{id}` | + takeoff/bom |
| POST/PATCH/DELETE | `/api/sheets/{id}/boxes`, `/api/boxes/{id}` | + takeoff/bom |

## Example: upload

```http
POST /api/documents
Content-Type: multipart/form-data

file=@data/plans/escondido_plans.pdf
```

```json
{
  "document_id": "...",
  "sheets": [
    { "sheet_id": "...", "page_index": 0, "job_id": "..." },
    { "sheet_id": "...", "page_index": 1, "job_id": "..." },
    { "sheet_id": "...", "page_index": 2, "job_id": "..." },
    { "sheet_id": "...", "page_index": 3, "job_id": "..." }
  ]
}
```

Poll `GET /api/jobs/{job_id}` until `status=succeeded`, then `GET /api/sheets/{sheet_id}`.

## Example: create detection

```http
POST /api/sheets/{sheet_id}/detections
Content-Type: application/json

{
  "category": "light",
  "subtype": "recessed",
  "center": { "x": 1000.0, "y": 200.0 },
  "room_source": "auto"
}
```

Response: `{ "detection": {...}, "takeoff": { "rows", "totals", "unassigned" } }`.

## Example: move / manual room

```json
PATCH /api/detections/{id}
{ "center": { "x": 950, "y": 400 } }
```

```json
PATCH /api/detections/{id}
{ "room_id": "<room uuid from sheet>", "room_source": "manual" }
```

## Notes for the UI

- Coordinates are PDF points, origin top-left; overlay `viewBox` = sheet viewport.
- Detection entity ids from FakeEngine look like `det-fan-1__a1b2c3d4` (uniquified per run).
- Same PDF re-upload returns the same `document_id` and succeeded jobs (idempotent).
- Demo CLI: `uv run python backend/scripts/demo_upload.py`
