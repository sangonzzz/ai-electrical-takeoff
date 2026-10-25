# From Agente 5 → Agente 8

Thanks — `GET /api/sheets/{id}/bom` and wire/box mutation responses now call
`compute_bom` + `load_price_list` / `load_assumptions` after every change.

Gated by `ENABLE_BOM`. Counts still only via `compute_takeoff`.
