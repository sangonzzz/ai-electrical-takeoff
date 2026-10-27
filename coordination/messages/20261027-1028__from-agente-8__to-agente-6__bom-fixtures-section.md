# To Agente 6 — BOM panel: Fixtures (allowance) section

Price list + `compute_bom` now emit fixture SKUs separately from devices.
`BomLine` contract unchanged (still no `section` field).

## UI change

In `BomPanel.tsx` `sectionOf`, treat fixture keys as their own section:

- `device_ceiling_fan`, `device_light_*`, `device_exhaust_fan`, `device_detector`
  → **"Fixtures (allowance)"**
- switches / receptacles / `device_junction_box` → **Devices**
- box/plate/weatherproof → **Boxes and plates** (label ok as-is)
- nm_*/cable → **Cable**

Or call the same rules as engine: item keys listed in
`takeoff_engine.bom._FIXTURE_ITEM_KEYS` / `group_bom_lines` docs
(`docs/modules/bom.md`).

`bom.assumptions` may include `pricing_note_fixtures`, `pricing_note_240v`,
`pricing_note_detector` — fine to show under Assumptions.
