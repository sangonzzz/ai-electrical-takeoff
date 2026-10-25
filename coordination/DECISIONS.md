# Decisions (counting rules and assumptions)

Owned by Agente 1. Others request changes via `coordination/messages/`.
Copied from `docs/SPEC.md` section 2 so agents have a short reference.

## Counting rules

1. Kitchen and Dining are separate rooms only when the plan labels them separately
   (Plan 2: yes; Plans 1 and 3: one room "Kitchen / Dining").
2. A component outside the building footprint counts under the room "Exterior"
   (porch light, WP receptacle, outdoor heat pump receptacle).
3. A combined fixture counts once under its combined type (fan/light, smoke/CO).
4. Switch type follows the letter next to the switch symbol, as defined by that
   sheet's legend and notes.
5. Assumption: the ceiling fan symbol includes a `J` circle at its center. It
   counts as ONE ceiling fan, not as a ceiling fan plus a junction box. A
   standalone `J` circle is a junction box.
6. Assumption: devices inside the "IN ATTIC" box belong to a room "Attic"
   (kind `attic`).
7. Assumption: open-plan boundaries between labels are split by nearest label
   (see rooms algorithm). The boundary is drawn on the plan and the user can
   reassign any detection.
8. Repeated labels get a suffix in display name: "CL 1", "CL 2" (ordered left
   to right, top to bottom).
9. Only the electrical plan viewport is analyzed; mechanical and finish plans
   are excluded.

## Count keys

Detections use `category` + `subtype`. Count keys are `category` and
`category.subtype` (see taxonomy in SPEC section 2 / `models.SUBTYPES`).

## Receptacle subtype priority

When several codes apply: `240V` > `MW` / `DW` / `H` / `FC` > `WP` > half-hot >
`GFI` > `AFI` > plain duplex.

## Scaffold decisions (Agente 1)

- Git author email: public GitHub email `santiagonzalezmora@gmail.com` (emails API
  lacked `user` scope; noreply fallback not needed).
- Page 2 electrical viewport left out of `APPROX_VIEWPORTS` until Agente 2 derives it.
- Unassigned detections still increment sheet `totals` so home totals match every
  active mark on the plan.
