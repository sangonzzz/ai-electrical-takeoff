# From Agente 5 → Agente 6

## Fix: GET /api/documents/{id} now keeps job polling alive

Root cause of “Queued forever”: after the first refetch, document sheets had no
`job_id` / `status`, so the UI lost the jobs and cards stayed Queued.

Each entry in `sheets` now includes:

| Field | Meaning |
|-------|---------|
| `sheet_id` | unchanged |
| `page_index` | unchanged |
| `sheet_number` | optional |
| `title` | optional |
| `current_run_id` | same as before |
| **`job_id`** | latest analysis run id (poll `/api/jobs/{job_id}`) |
| **`status`** | `queued` \| `running` \| `succeeded` \| `failed` \| `null` |
| **`error`** | string if `status=failed`, else `null` |

Example sheet row:

```json
{
  "sheet_id": "...",
  "page_index": 0,
  "sheet_number": "A1-111",
  "title": "ELECTRICAL PLAN - PLAN 1",
  "current_run_id": "...",
  "job_id": "...",
  "status": "succeeded",
  "error": null
}
```

You can poll `GET /api/documents/{id}` every 2 s and drive card status from
`sheets[].status` / `job_id` without a separate jobs map.
