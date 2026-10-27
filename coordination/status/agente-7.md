# Agente 7 — Evaluation, overlay, CI checks

## Estado

Golden refresh **bloqueado**. Plan 1–2 solo cambian cuartos (pocket rule de A3);
plan 3 pierde una detección; plan 4 cambia `needs_review`. No reescribí
`eval/golden/v0.6.4/`.

## Diff vs golden v0.6.4 (current code, `use_llm=False`, `with_bom=True`)

Script: `eval/scripts/diff_golden_vs_current.py` → report
`out/debug/golden_room_diff_report.md` (gitignored).

### Non-room fingerprint (dets without room_id, wires, boxes, sheet)

| plan | non-room equal? | notes |
|------|-----------------|-------|
| 1 | **yes** | |
| 2 | **yes** | |
| 3 | **no** | −1 det, −1 box, wire set changes |
| 4 | **no*** | *equal if `needs_review` ignored; 2 flags flip True→False |

### Plan 1 — rooms only (OK to refresh when unblocked)

- Room count **12 → 9**
- Removed rooms: `Mech. Closet (B14)`, `Mech. Closet (B32)`, `Unlabeled space 1`
- Detection reassignments (2):
  - `receptacle.gfci_240v` @ (1151.94, 197.46): `Unlabeled space 1` → `Exterior`
  - `receptacle.gfci_240v` @ (1322.22, 222.06): `Mech. Closet (B14)` → `Bath`

### Plan 2 — rooms only

- Room count **16 → 12**
- Removed: `Mech. Closet (B32)`, `Unlabeled space 1`, `Unlabeled space 2`, `Unlabeled space 3`
- Reassignment (1):
  - `receptacle.gfci_240v` @ (1050.42, 223.14): `Unlabeled space 3` → `Laundry`

### Plan 3 — **extra non-room delta (blocks refresh)**

- Rooms: **33 → 14**; many `Unlabeled space N` + `Mech. Closet (A01)` removed; 22 room reassignments (samples in debug report).
- **Also:** missing `receptacle.afci_half_hot` @ **(895.8, 505.68)** vs golden; box at same center gone; wire fingerprints −2/+1.
- Messaged Agente 2 / 3 / 1.

### Plan 4 — rooms + needs_review

- Rooms: **37 → 16**; many unlabeled pockets removed; 25 room reassignments.
- Geometry of dets/wires/boxes match golden; `needs_review` flips on:
  - `receptacle.gfci_240v` @ (1820.82, 296.94): True → False
  - `receptacle.gfci_weatherproof` @ (1345.98, 567.42): True → False

## Hecho

- Diff harness `eval/scripts/diff_golden_vs_current.py`
- Messages to A1/A2/A3; **no golden rewrite** (rule not met)

## Cómo probarlo

```bash
uv run python eval/scripts/diff_golden_vs_current.py
uv run pytest engine/tests/eval/test_golden.py -q   # expect fail until refresh
```

## Siguiente

- Wait for A2 on plan3 half-hot, or Santiago OK to absorb that + needs_review into new golden.
- Then regenerate all four `eval/golden/v0.6.4/planN.json` from current code and commit.

## Bloqueos

Cannot refresh goldens under Santiago’s rooms-only gate until plan3 det delta is resolved.

## Decisions

- Treat missing detection / wire / box as hard blocker (not “pocket rename”).
- `needs_review` alone would not block if Santiago confirms it is out of golden scope;
  still held with plan3.

## Needs from Santiago

Confirm whether to absorb plan3 half-hot loss (+ plan4 needs_review) into the new golden,
or require A2 restore first.

## Explicación para Santiago

Agente 3 apretó la regla de “bolsillos” sin etiqueta. Comparé el motor actual con el
golden v0.6.4: en **planos 1 y 2** solo cambian nombres/asignaciones de cuartos (como
pediste). En **plan 3** además **desaparece un tomacorriente half-hot** (y su caja/cables).
En **plan 4** dos marcas cambian `needs_review`. Por eso **no regeneré** el golden: el
candado seguiría siendo honesto. Cuando digas que absorbemos ese delta (o A2 restaure
el half-hot), regenero los 4 JSON y dejo `test_golden` en verde otra vez.
