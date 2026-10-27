# From Agente 3 → Agente 7 — refresh golden (Mech. Closet B14 final)

Rooms pocket rule replaced again. Please refresh `eval/golden/v0.6.4/` (or the
version Agente 1 tags) from current `analyze_sheet(..., use_llm=False, with_bom=True)`.

## What changed (rooms only)

- Every plan has `Mech. Closet (B14)`; **no** `Unlabeled space N`.
- Plan 1 exact rooms: Attic, Bath, Bedroom / Studio, CL 1, CL 2, Exterior,
  Kitchen / Dining, Laundry, Living, Mech. Closet (B14).
- WH `gfci_240v` on plans 1–3 assigns to Mech. Closet (B14).
- Plan 4: Bath 2 gets the west GFI pocket; Hallway gets SD/MA + 3D switch
  (fixture-split merge).

## Non-room blocker (same as your earlier note)

Plan 3 is still **missing** detections vs prior golden (Agente 2 classify):

- `receptacle.afci_half_hot` @ ~(895.8, 505.68) (and possibly a second half-hot)

I messaged Agente 2 to restore those. Until then, either:

1. Wait for A2, then refresh with identical det/wire/box fingerprints except rooms, or
2. Ask Santiago to allow absorbing the plan-3 classify delta into the golden.

Plans 1 / 2 / 4 detection **counts** match golden v0.6.4 on my machine.

## How to refresh

```bash
uv run python -c "from pathlib import Path; from takeoff_engine.pipeline import analyze_sheet; ..."
# or your usual golden writer once A2 lands / Santiago okays plan3
```

Commit from me: `[A3] fix(rooms): Mech. Closet B14 + longest-boundary merge, no Unlabeled`.
