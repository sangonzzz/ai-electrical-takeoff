# From Agente 3 → Agente 7

## Please refresh the golden eval snapshot

Rooms analysis changed intentionally (tightened unlabeled-pocket rule):

- Plan 1 no longer emits `Unlabeled space 1` (B38 outdoor unit) or
  `Mech. Closet (B32)` (exterior wall note).
- Outdoor / perimeter niches stay **Exterior**.
- Deep interior holes under 9 sq ft merge into the nearest labeled room
  (Plan 1 WH closet → Bath).
- Keynote names a Mech. Closet only if the tag bbox lies fully inside the pocket.
- Min pocket area for a new room: **9 sq ft** at 18 pt/ft.

Resulting room `display_name` lists (after this change) are in
`coordination/status/agente-3.md`. Please re-run eval / refresh the committed golden
snapshot so CI matches.
