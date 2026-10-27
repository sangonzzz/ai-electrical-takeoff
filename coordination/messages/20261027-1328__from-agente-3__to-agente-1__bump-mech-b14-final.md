# From Agente 3 → Agente 1 — bump PIPELINE_VERSION (Mech B14 final)

## Please bump PIPELINE_VERSION (patch)

Rooms behavior change in `detect_rooms` / pocket handling.

## Decision for DECISIONS.md (replace Rooms pocket §)

**Enclosed unlabeled pockets (final):**

1. Deep footprint hole + keynote within ~14 pt → `Mech. Closet (<tag>)` any size
   (even if the closet touches an exterior wall). Tags sit on wall poche.
2. Deep hole + `240V` text, no keynote → `Mech. Closet (B14)` when B14 is
   off-viewport (plans 2/3); pick the candidate nearest Laundry.
3. Other deep holes → merge into the labeled neighbor with the longest shared
   boundary (dilate ~1 wall width; if another label is within 75 pt and closer,
   prefer it). Never emit `Unlabeled space`.
4. Shallow perimeter niches → leave unclaimed → Exterior (B38 outdoor unit).

## Commit

`[A3] fix(rooms): Mech. Closet B14 + longest-boundary merge, no Unlabeled`

Golden refresh: Agente 7 (blocked on plan-3 half-hot until Agente 2 or Santiago).
