# Fresh analysis button → `POST /api/sheets/{id}/reanalyze`

From: Agente 5  
To: Agente 6  
Date: 2026-10-27

## Endpoint (already on OpenAPI)

`POST /api/sheets/{sheet_id}/reanalyze` → **202**

```json
{ "sheet_id": "...", "job_id": "<new run id>", "status": "queued" }
```

## Semantics (for the UI button)

1. Creates a **new** analysis run (does not reuse idempotent succeeded runs).
2. **Does not** delete old runs or their corrections.
3. `current_run_id` switches only when the new job **succeeds** — keep polling
   `GET /api/jobs/{job_id}` (and/or document sheets) like upload.
4. After success, `GET /api/sheets/{id}/corrections` and `/history` are **empty**
   for the new run (fresh slate). Prior correction rows remain in DB on old runs.

Wire a “Fresh analysis” / “Re-run” control to this POST, then poll until
`succeeded` | `failed` and refresh the sheet bundle.
