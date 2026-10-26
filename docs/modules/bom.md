# Bill of materials (wires, boxes, pricing)

Owner: **Agente 8**. Pure functions so the backend recomputes after any CRUD change.

## What it does

1. **`find_wire_runs`** — chain dashed black strokes in the electrical viewport into device-to-device `WireRun` polylines, measure length in feet, assign cable type.
2. **`compute_boxes`** — group nearby switches into multi-gang boxes; assign box kind and cover per device rules.
3. **`compute_bom`** — aggregate devices, boxes, plates/covers, and cable (feet + rolls) into priced `Bom` lines with `source_ids`.
4. **`load_price_list` / `load_assumptions`** — YAML loaders for `data/price_list.yaml` and `data/assumptions.yaml`.

## Measured dash geometry (Plan 1, page 0)

Inside `config.APPROX_VIEWPORTS[0]`, black open strokes (width ≈ 0.24) that form dashed wiring:

| Quantity | Measured value |
|----------|----------------|
| Dash length (median) | **7.1 pt** |
| Dash length (typical range) | **4–10 pt** |
| Gap (median, wiring-like pairs) | **3.8 pt** |
| Gap (typical range) | **2–4.5 pt** |

Detector window used in code: dash length **3–12 pt**, gap **1–6 pt** (margin around the measurement). Documented also in `data/assumptions.yaml`.

## Wire algorithm

1. Collect short black segments in the viewport (stroke width ≈ 0.24, length in window).
2. Build a proximity graph: edge if any endpoints are within the gap window.
3. Connected components → candidate chains; drop tiny components (symbol fragments: need ≥3 dashes or ≥20 pt total ink).
4. Order each component into a polyline (walk from a degree-1 end; soft direction preference when several neighbors exist).
5. Associate detections along the dashed polyline within `WIRE_PATH_ASSOCIATE_PT` (28 pt); if fewer than two, enrich with nearest devices to each endpoint within `WIRE_END_ASSOCIATE_PT` (32 pt). (`WIRE_SNAP_PT`=10 alone is too tight for real symbol centers.) Consecutive devices along a chain become hops; each hop keeps the **sub-polyline of dashes** (never invent a bare center-to-center chord).
6. **Phantom chord gate:** reject only if the polyline is nearly straight (chord/length ≥ 0.90) **and** more than 30% of samples lack a nearby dash. Curved dash-following runs are kept.
7. **Length:** polyline length / `scale_pt_per_ft` → `plan_length_ft`.
8. **Cable type:** `nm_14_3` if both ends are `three_way` or `three_way_dimmer`; else `nm_14_2`.
9. **Vertical allowance** (from assumptions): switch end → `(ceiling_height_ft − switch_height_in/12) + slack`; ceiling-ish end → `slack` only; wall receptacles/lights use mount height when known. Waste is **not** applied here — it is applied in `compute_bom`.

### Routing assumption (honest limit)

Dashed lines on the plan show **connectivity**, not the real cable route through studs and joists. We measure the drawn polyline, then add vertical drops/rises and slack from `assumptions.yaml`, then +10% waste for purchasing.

## Box rules

| Device | Box `kind` | Gangs | Cover |
|--------|------------|-------|-------|
| Switches within `GANG_GROUP_DIST_PT` (10 pt) on the same wall | `device` | n | `plate` |
| Receptacle | `device` | 1 | `plate`, or `weatherproof_cover` if WP |
| Ceiling fan | `fan_rated` | 1 | `none` |
| Pendant, wall, exterior light; detector; junction box | `ceiling_round` | 1 | `none` |
| Recessed light; exhaust fan | `none` (integrated housing) | 1 | `none` |

Same wall = centers share x or y within 3 pt. Deleted detections are ignored.

## BOM lines

- **Devices** keyed by taxonomy → `item_key` (e.g. `switch_single_pole`, `device_light`).
- **Boxes** by kind/gangs (`box_1gang`, `box_2gang`, `box_fan_rated`, …).
- **Covers** (`plate_1gang`, `plate_2gang`, `weatherproof_cover`).
- **Cable:** `{nm_14_2\|nm_14_3}_ft` (with waste) and `{…}_roll_250` (`ceil(ft / cable_roll_ft)`).
- Each line has `source_ids` (detection / box / wire ids).
- `total_usd` sums only lines with a known `extended_price`.

## Price sources

`data/price_list.yaml`: Home Depot URLs, `captured_at`, `verified` flag. **Never invent a price** — if unverified, `unit_price` is null and `verified: false`.

Verified examples (2026-10-25): 14/2 250 ft roll $125; 14/3 250 ft $165; 1-gang box $2.37; 2-gang $3.38; fan-rated ceiling box $8.38; 1-gang plate $0.88; WP cover $5.98; single-pole switch $0.98.

## Parameters / thresholds

| Name | Value | Why |
|------|-------|-----|
| `WIRE_SNAP_PT` | 10 | Spec snap radius to device centers |
| `GANG_GROUP_DIST_PT` | 10 | Spec multi-gang grouping |
| Dash / gap windows | see above | Measured on Plan 1 |
| `ceiling_height_ft` | 8 | Stated routing assumption |
| `switch_height_in` | 48 | AFF for switch vertical |
| `slack_ft_per_end` | 1 | Spec |
| `waste_fraction` | 0.10 | Spec |

## Public API (for backend / frontend)

```python
find_wire_runs(ctx, viewport, detections, scale_pt_per_ft, assumptions) -> list[WireRun]
compute_boxes(detections, sheet_id) -> list[Box]
compute_bom(sheet_id, detections, wire_runs, boxes, prices, assumptions) -> Bom
load_price_list(path=None) -> dict[str, dict]   # keyed by item_key
load_assumptions(path=None) -> dict
```

`Bom.assumptions` includes the routing numbers plus a `routing_note` string for the UI.

## Known limits

- Dashed plan ink ≠ true cable path (routing assumption required).
- Until Agente 2 detections exist, wire snaps on real PDFs should use real centers; tests use fixtures + virtual endpoints for debug PNGs.
- Fixture detection centers are hand-placed — box overlays on the real PDF may not align; use `out/debug/boxes_fixture_schematic.png` for grouping evidence.
- Some specialty device/plate SKUs are `verified: false` pending Santiago.
- Chains can still pick up dense symbol clusters; component size filter reduces but does not eliminate false runs.
- Phantom gate only rejects nearly-straight uncovered chords; short straight hops that sit on dashes are kept.
- `MAX_PLAN_LENGTH_FT` (40) drops bogus mega-merges; legitimate long home-runs on large sheets may need a higher cap later.
- 4+ gang boxes map to the 3-gang price key as the closest listed SKU.

## Debug artifacts

```bash
.venv/Scripts/python engine/tests/bom/render_debug.py
# → out/debug/wires_plan1.png
# → out/debug/boxes_plan1.png
# → out/debug/boxes_fixture_schematic.png
```
