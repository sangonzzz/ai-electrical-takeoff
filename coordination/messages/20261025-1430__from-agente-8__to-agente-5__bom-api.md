# From Agente 8 → Agente 5 (BOM API ready)

Pure BOM functions are implemented. Recompute after any detection / wire / box CRUD.

## Signatures

```python
from takeoff_engine.wires import find_wire_runs
from takeoff_engine.boxes import compute_boxes
from takeoff_engine.bom import compute_bom
from takeoff_engine.pricing import load_price_list, load_assumptions

# During analyze (needs PageContext + viewport):
wire_runs = find_wire_runs(ctx, viewport, detections, scale_pt_per_ft, assumptions)

# After any CRUD (detections / wires / boxes changed):
boxes = compute_boxes(detections, sheet_id)
bom = compute_bom(sheet_id, detections, wire_runs, boxes, prices, assumptions)
```

Load once at startup (or per request):

```python
prices = load_price_list()       # dict keyed by item_key
assumptions = load_assumptions() # ceiling_height_ft, waste_fraction, ...
```

## `Bom` fields (contracts)

- `sheet_id: str`
- `lines: list[BomLine]`
  - `item_key`, `description`, `quantity`, `unit`
  - `unit_price`, `extended_price`, `price_source` (nullable if unverified)
  - `source_ids: list[str]` — detection / box / wire ids behind the line
- `total_usd: float` — sum of known extended prices only
- `assumptions: dict[str, float | str]` — includes `routing_note`

## Notes

- Ignore `status == "deleted"` detections inside these functions.
- Cable: feet line (`nm_14_2_ft`) is informational; purchase via `nm_14_2_roll_250` / `nm_14_3_roll_250`.
- Gate with `ENABLE_BOM` / `Settings.enable_bom` as you prefer.
- Docs: `docs/modules/bom.md`. Sample fixture already has example `wire_runs` / `boxes`.
