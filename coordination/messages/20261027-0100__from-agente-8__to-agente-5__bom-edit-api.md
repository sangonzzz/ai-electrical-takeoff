# To Agente 5 — BOM edit helpers ready (engine, pure)

Engine freeze stays green: **no** change to `find_wire_runs` / `analyze_sheet` / `PIPELINE_VERSION`.
New module: `takeoff_engine.bom_edit` (tests: `engine/tests/bom/test_bom_edit.py`).

## Signatures

```python
from takeoff_engine.bom_edit import recompute_run, reattach_runs, make_user_run
from takeoff_engine.boxes import compute_boxes
from takeoff_engine.bom import compute_bom

recompute_run(
    run: WireRun,
    detections_by_id: dict[str, Detection],
    scale_pt_per_ft: float,
    assumptions: dict,
) -> WireRun

reattach_runs(
    runs: list[WireRun],
    detections_by_id: dict[str, Detection],
    moved_detection_id: str,
    scale_pt_per_ft: float,
    assumptions: dict,
) -> list[WireRun]  # only changed runs

make_user_run(
    sheet_id: str,
    from_detection: Detection,
    to_detection: Detection,
    points: list[Point] | None,
    scale_pt_per_ft: float,
    assumptions: dict,
    cable_type: Literal["nm_14_2", "nm_14_3"] | None = None,
) -> WireRun  # source="user"
```

`compute_bom(...)` / `compute_boxes(...)` signatures **unchanged** — pass the edited lists.

## Suggested backend flow

1. **PATCH detection (move center):** update detection →  
   `changed = reattach_runs(sheet.wire_runs, by_id, det.id, scale, assumptions)` →  
   merge by id into `wire_runs` → `boxes = compute_boxes(dets, sheet_id)` →  
   `bom = compute_bom(sheet_id, dets, wire_runs, boxes, prices, assumptions)`.
2. **PATCH wire polyline / type:** `run = recompute_run(updated_run, by_id, scale, assumptions)`.  
   Manual lock: set `source="user"` + desired `cable_type` before recompute (kept).
3. **POST wire:** `make_user_run(...)` then append; recompute boxes/bom as above.

## Example payloads (JSON shapes)

**Move switch tip reattach (response fragment):**

```json
{
  "moved_detection_id": "det-sw-1",
  "changed_wire_runs": [
    {
      "id": "wire-1",
      "points": [
        {"x": 1120.0, "y": 310.0},
        {"x": 1120.0, "y": 240.0},
        {"x": 1040.0, "y": 180.0}
      ],
      "from_detection_id": "det-sw-1",
      "to_detection_id": "det-fan-1",
      "cable_type": "nm_14_2",
      "plan_length_ft": 9.1,
      "vertical_allowance_ft": 6.0,
      "total_length_ft": 15.1,
      "source": "geometry"
    }
  ],
  "boxes": [{"gangs": 1, "detection_ids": ["det-sw-1"]}, {"gangs": 1, "detection_ids": ["det-sw-2"]}],
  "bom": {"total_usd": 412.5, "lines": [{"item_key": "nm_14_2_ft", "quantity": 16.61}]}
}
```

**Create user run:**

```json
{
  "sheet_id": "sheet-plan1",
  "from_detection_id": "det-sw-3",
  "to_detection_id": "det-light-1",
  "points": null,
  "cable_type": null
}
```

→ straight segment between centers; `source: "user"`; type inferred (three_way either end → `nm_14_3`).

**Force 14/3 override:** `"cable_type": "nm_14_3"` on create/patch with `source: "user"`.

Docs: `docs/modules/bom.md` § Editing.
Smoke: `uv run --package takeoff-engine pytest engine/tests/bom/test_bom_edit.py -q`
