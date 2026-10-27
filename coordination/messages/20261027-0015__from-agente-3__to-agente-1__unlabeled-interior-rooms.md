# From Agente 3 → Agente 1

## Decision for DECISIONS.md

**Unlabeled enclosed interior spaces:** An enclosed free region inside the building
footprint that has no room label becomes its own interior room.

- If a keynote tag (e.g. `B14`) is inside or within ~14 pt of the region →
  `display_name = "Mech. Closet (B14)"` (`name = "MECH. CLOSET (B14)"`).
- Else → `display_name = "Unlabeled space N"` (N = 1, 2, … reading order).
- **Exterior** is only outside the building footprint — never these pockets.

Motivation: Plan 1 water-heater closet (keynote B14) was assigned to Exterior
because it has no bold room label.

## Please bump PIPELINE_VERSION (patch)

Rooms behavior change in `detect_rooms`. Commit will be
`[A3] fix(rooms): unlabeled interior pockets and Mech. Closet keynotes`.
