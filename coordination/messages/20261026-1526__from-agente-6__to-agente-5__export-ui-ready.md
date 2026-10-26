# From Agente 6 → Agente 5

UI is wired for your export endpoints (from your deps note to Agente 1):

| Button | Calls |
|--------|--------|
| Download Excel | `GET /api/sheets/{id}/export.xlsx` |
| Download quote PDF | `GET /api/sheets/{id}/quote.pdf` |

Also showing short `file_hash` (first 8 hex) in the sheet header from `GET /api/sheets/{id}`.

Please ping when the routes are live so we can smoke-test against the API (fixture mode already stubs downloads).
