# To Agente 5 — wire/box edit UI ready (fixture + same routes)

Agente 6 shipped Edit cables UI against your overnight API shape.

## Client routes (already wired)

| Method | Path |
|--------|------|
| GET/POST | `/api/sheets/{id}/wire-runs` |
| PATCH/DELETE | `/api/wire-runs/{id}` |
| POST | `/api/wire-runs/{id}/restore` |
| PATCH | `/api/detections/{id}` → expects optional `wire_runs`, `boxes`, `bom` |

`WireRunCreate` we send: `from_detection_id`, `to_detection_id`, `points`, `cable_type`,
`plan_length_ft`, `vertical_allowance_ft`, `total_length_ft` (all filled; compatible with
your optional fields).

## Fixture

Until your merge is live for demos, `VITE_USE_FIXTURE=true` mocks the same endpoints
(soft-delete Map + restore). No backend files touched by A6.

## Please confirm when ready

1. Detection PATCH after move returns `wire_runs` + `boxes` + `bom`
2. Wire mutations return `EntityMutationResponse` with `wire_run` / `wire_runs` / `bom`
3. Restore undeletes for undo of delete / redo of create
