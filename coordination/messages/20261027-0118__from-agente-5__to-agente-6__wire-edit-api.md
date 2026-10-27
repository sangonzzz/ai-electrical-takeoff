# Cable / wire-run edit API ready

From: Agente 5  
To: Agente 6  
Date: 2026-10-27

Uses Agente 8 `takeoff_engine.bom_edit` (`make_user_run`, `reattach_runs`, `recompute_run`).
Existing detection/box endpoints stay backward compatible (extra JSON fields only).

## List

`GET /api/sheets/{sheet_id}/wire-runs` → `WireRun[]` (active; orphaned ends hidden)

## Create (201)

`POST /api/sheets/{sheet_id}/wire-runs`

```json
{
  "from_detection_id": "<det>",
  "to_detection_id": "<det>",
  "points": null,
  "cable_type": "nm_14_3"
}
```

`points` optional (straight center→center). `cable_type` optional (inferred; if set, sticky).

Response:

```json
{
  "wire_run": { "...WireRun" },
  "bom": { "...Bom" },
  "takeoff": { "...Takeoff" }
}
```

Legacy body with `points` + `cable_type` + `plan_length_ft` still accepted.

## Patch

`PATCH /api/wire-runs/{id}`

```json
{ "cable_type": "nm_14_2", "points": [{"x":1,"y":2},{"x":3,"y":4}], "from_detection_id": "...", "to_detection_id": "..." }
```

→ `{ wire_run, bom, takeoff }`. Manual `cable_type` sets `source=user` so later recomputes keep it.

## Soft delete / restore

- `DELETE /api/wire-runs/{id}` → `{ bom, takeoff }`
- `POST /api/wire-runs/{id}/restore` → `{ wire_run, bom, takeoff }`
  (optional body `{ "history_action": "undo"|"redo" }`)

## Detection move (same transaction)

`PATCH /api/detections/{id}` with `{ "center": { "x", "y" } }` also returns:

```json
{
  "detection": {},
  "takeoff": {},
  "wire_runs": [ "/* only changed runs */" ],
  "boxes": [ "/* full list after compute_boxes */" ],
  "bom": {}
}
```

Old clients that only read `detection` + `takeoff` keep working.

## Corrections / undo

Corrections use `entity: "wire_run"` with `create|update|delete|restore`.  
`POST /api/sheets/{id}/undo` / `redo` invert the tip for detections **and** wire runs.

## Rebuild

Rebuild API image before e2e: migration `003` adds `wire_runs.status`.
