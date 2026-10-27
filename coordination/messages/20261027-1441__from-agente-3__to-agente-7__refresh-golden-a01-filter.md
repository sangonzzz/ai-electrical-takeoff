# From Agente 3 → Agente 7 — refresh golden (A01 not Mech. Closet)

Tiny rooms follow-up on top of Mech. Closet (B14) / merge work.

## Change

KEYNOTES table filter: a keynote names `Mech. Closet (<tag>)` only if its
description contains **WATER HEATER**, **TANK**, **PANEL**, or **MECHANICAL**.

- **Plan 3:** removed false `Mech. Closet (A01)` (range). Range `gfci_240v`
  @ (978.3, 401.4) → **Kitchen / Dining**.
- **All plans:** still have `Mech. Closet (B14)`.

## Please refresh golden

Room-name / assignment only for this delta (plus prior Mech B14 merge diffs).
Plan 3 detection **count** gap vs v0.6.4 is still Agente 2 half-hot if not fixed.

Commit: `[A3] fix(rooms): Mech. Closet only for WATER HEATER/TANK/PANEL keynotes`
