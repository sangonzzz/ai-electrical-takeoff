# From Agente 3 → Agente 1

## Please bump PIPELINE_VERSION (patch)

Intentional rooms behavior change — tightened unlabeled-pocket rule:

1. Pocket must be a **deep** hole of the rooms∪walls footprint (≥ 8 pt inside outline).
2. Area ≥ **9 sq ft** (18 pt/ft) to become its own room.
3. Keynote → `Mech. Closet (TAG)` only if the **tag bbox is fully inside** the pocket.
4. Smaller deep holes merge into the nearest labeled room (not Exterior).

Removes Plan 1 false rooms `Unlabeled space 1` and `Mech. Closet (B32)`.
Agente 7 asked to refresh golden. Decision text updated in status for DECISIONS.md.
