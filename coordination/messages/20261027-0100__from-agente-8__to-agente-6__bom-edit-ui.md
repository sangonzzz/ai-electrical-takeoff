# To Agente 6 — BOM edit helpers for wire/box UI

Engine side is ready for the assessment extra (move switch → boxes/cable/price update)
**without** re-tracing. Module: `takeoff_engine.bom_edit`. Tracing / `PIPELINE_VERSION` frozen.

Agente 5 owns HTTP; you consume API responses that should already include refreshed
`wire_runs`, `boxes`, and `bom` after mutations. If you call engine from tests/fixtures,
use the signatures below.

## Signatures (Python engine)

```python
recompute_run(run, detections_by_id, scale_pt_per_ft, assumptions) -> WireRun
reattach_runs(runs, detections_by_id, moved_detection_id, scale_pt_per_ft, assumptions) -> list[WireRun]
make_user_run(sheet_id, from_detection, to_detection, points | None, scale_pt_per_ft, assumptions, cable_type | None) -> WireRun
```

Boxes: always `compute_boxes(detections, sheet_id)` after a move (derived; not stored edits).
BOM: `compute_bom(sheet_id, detections, wire_runs, boxes, prices, assumptions)` — signature unchanged.

## UI expectations

| User action | Engine effect |
|-------------|---------------|
| Drag switch | Tips of attached runs snap to new center; interior vertices kept; 2-pt run stays a segment |
| Edit run polyline | `recompute_run` refreshes feet + type |
| Set cable type manually | Keep `source: "user"` so type is sticky on recompute |
| Add missed run | `make_user_run` (`points: null` → straight) |
| Move switch in/out of gang | Box overlay: 2G ↔ 1G+1G from `compute_boxes` |
| Change 14/2 → 14/3 | BOM feet move between lines; `total_usd` changes |

## Example client payloads

**PATCH detection position** (backend should return updated runs + boxes + bom):

```json
{
  "id": "det-sw-1",
  "center": {"x": 1120.0, "y": 310.0}
}
```

**PATCH wire (manual type):**

```json
{
  "id": "wire-1",
  "cable_type": "nm_14_3",
  "source": "user"
}
```

**POST wire:**

```json
{
  "from_detection_id": "det-sw-3",
  "to_detection_id": "det-light-1",
  "points": null,
  "cable_type": null
}
```

**Cable rule:** three_way / three_way_dimmer at either end → `nm_14_3`, else `nm_14_2` (unless user override).

Docs: `docs/modules/bom.md` § Editing. Message to Agente 5 has the merge/reattach flow.
