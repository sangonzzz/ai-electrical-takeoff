# From Agente 8 → Agente 6 (BOM UI fields)

BOM is ready to display. Backend will expose it via `GET /api/sheets/{id}/bom` (Agente 5); the payload matches contracts `Bom` / `BomLine`.

## What to show in the BOM panel

- **Assumptions** (from `bom.assumptions`): ceiling height, switch AFF, slack, waste %, plus `routing_note`  
  (“Dashed plan lines show connectivity, not the true cable route.”).
- **Lines table:** description, qty, unit, unit price, extended, price source.
- **Total:** `bom.total_usd` (only verified/priced lines contribute).
- Clicking a line can highlight `source_ids` on the plan (detections / boxes / wire runs).

## Overlay labels (SPEC §10)

- Wires: e.g. `14/2 - 12.4 ft` from `cable_type` + `total_length_ft` (or plan length — pick one and stay consistent; we store both).
- Boxes: `2G`, `3G`, … from `box.gangs` (skip `kind == "none"`).

## Cable item keys

- `nm_14_2_ft` / `nm_14_3_ft` — quantity in feet (includes waste)
- `nm_14_2_roll_250` / `nm_14_3_roll_250` — rolls to buy (priced)

Unverified prices have `unit_price: null` — show “—” rather than inventing a number.

## Types

Shared contracts already include `WireRun`, `Box`, `Bom`, `BomLine` in `web/src/types/contracts.ts` (Agente 1). See `docs/modules/bom.md` for rules.
