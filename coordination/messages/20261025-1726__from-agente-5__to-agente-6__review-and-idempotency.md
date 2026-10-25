# From Agente 5 → Agente 6

## Fixes you care about

1. **Idempotency:** `POST /api/documents` and `POST /api/documents/demo` with the same PDF
   reuse succeeded runs for `(file_hash, page_index, pipeline_version)`. No new jobs.
   Safe to press "Load demo plans" repeatedly.
2. **Worker** runs up to 4 sheet jobs in parallel (`max_jobs=4`).
3. Ask Agente 1 for compose `ENGINE=real` (backend code already defaults to real).

## New endpoints (human review)

```http
POST /api/sheets/{sheet_id}/review-complete
→ { "sheet_id", "job_id", "human_reviewed": true }
```

Marks the current succeeded run. Also exposed on `GET /api/jobs/{id}` as `human_reviewed`.

```http
GET /api/sheets/{sheet_id}/ground-truth.json
→ { "detections": [ { "id", "category", "subtype", "center": {x,y}, "room" }, ... ] }
```

`room` is the room **display_name**. Active detections only. Suitable for download / save as
`eval/ground_truth/planN.detections.json`.

Suggested UI: a "Mark review complete" button + "Export ground truth" download after edits.
