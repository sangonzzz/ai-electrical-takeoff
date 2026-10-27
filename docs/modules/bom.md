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

Detector (v3.1): **black (0,0,0) strokes only**. Visual dash ≈ **7 pt** / gap ≈ **3.8 pt**. After PDF flatten-join, collect open polyline components **4–14 pt**; link gaps **1.5–10 pt** with turn ≤ **45°** (nominal product window was 4–11 / 1.5–6 / 35° — Escondido tips need the wider window).

## Wire algorithm (v3.1)

1. **Dash** = open black stroke polyline (RGB ≤ 0.02, width ≈ 0.24), arc length 4–14 pt, after dropping primitives inside receptacle/detector (+ outdoor 240V) bboxes inflated **+2 pt**. Switch/light/fan bboxes are **not** carved so tip attach can still hit them. Continuous flatten joints (≤ 0.5 pt) merge into one dash; longer open paths are kept as whole curves.
2. **Link** dash A→B when nearest endpoints are 1.5–10 pt apart and direction change &lt; 45°.
3. A chain of **≥3** dashes is a wire. Reject only if it has **≥6** dashes **and** every point is within **1 pt** of the straight chord (millwork). Long continuous paths use the same chord test with virtual dash count ≈ length/7.
4. **Extend** each chain tip along its tangent up to **36 pt** (nominal 12; Escondido needs ~36 to bridge carved approaches); attach when the ray hits a device bbox. Drop chains that do not attach at both ends, or whose ends attach to the **same** device. Never attach to outdoor 240V / B38 equipment.
5. **Cable type (simple estimator):** any run with `three_way` / `three_way_dimmer` at **either** end → `nm_14_3`; everything else → `nm_14_2`.
6. **Known limit:** residual millwork can still leak; UI may keep Wires **beta** (Agente 6).

Debug PNGs: teal dash underlay + pink (`nm_14_2`) / green (`nm_14_3`) runs → `out/debug/wires_plan{1..4}.png`.

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
| `DASH_LEN_*` | 4–14 pt | Spec 4–11; flatten-join lands ~4–13.5 |
| `GAP_*` | 1.5–10 pt | Spec 1.5–6; Escondido tip gaps ~6.7–10 |
| `MAX_TURN_DEG` | 45 | Spec 35; real arcs turn more after flatten |
| `TANGENT_EXTEND_PT` | 36 | Spec 12; bridge tip → device bbox |
| `STRAIGHT_CHORD_TOL_PT` | 1.0 | Millwork reject (≥6 dashes, all pts ≤1 pt of chord) |
| `BBOX_EXCLUDE_INFLATE_PT` | 2.0 | Carve receptacle/detector glyphs |
| `GANG_GROUP_DIST_PT` | 10 | Spec multi-gang grouping (boxes) |
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
