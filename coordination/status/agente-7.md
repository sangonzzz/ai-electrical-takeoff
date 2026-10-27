# Agente 7 — Evaluation, overlay, CI checks

## Estado

Golden refresh **no hecho**. Re-diff vs `eval/golden/v0.6.4` (2026-10-27 ~13:41):
plans 1–2 rooms-only; plan 3 still missing a detection; plan 4 only `needs_review`.

## Diff re-run (current vs v0.6.4 golden)

Command: `uv run python eval/scripts/diff_golden_vs_current.py`  
(`use_llm=False`, `with_bom=True`, normalized fingerprint)

### Gate: detections / wires / boxes identical except room fields?

| plan | pass? | detail |
|------|-------|--------|
| 1 | **yes** | non-room fingerprint identical |
| 2 | **yes** | non-room fingerprint identical |
| 3 | **no** | see exact deltas below |
| 4 | **no** | only `needs_review` on 3 receptacles (geometry/wires/boxes match if that field ignored) |

→ **Did not refresh** `eval/golden/v0.6.4/*.json`.

### Plan 1 — rooms only (summary)

- Rooms **12 → 10**; removed `Mech. Closet (B32)`, `Unlabeled space 1`
- Still present: `Mech. Closet (B14)` (A3 final rule)
- Reassignment (1): `receptacle.gfci_240v` @ (1151.94, 197.46): `Unlabeled space 1` → `Exterior`

### Plan 2 — rooms only (summary)

- Rooms **16 → 13**; removed B32 + Unlabeled 1–3; **added** `Mech. Closet (B14)`
- Reassignment (1): `receptacle.gfci_240v` @ (1050.42, 223.14): `Unlabeled space 3` → `Mech. Closet (B14)`

### Plan 3 — exact non-room deltas (blocker)

- **Missing detection** vs golden: `receptacle.afci_half_hot` center **(895.8, 505.68)** (`needs_review=False`)
- Counts: detections **71 → 70**, boxes **69 → 68**, wire_runs **51 → 50** (geometry set also shifts: −2/+1 by polyline key)
- Cascading box remaps (stable ids renumber after the missing det); first missing box was 1-gang device at same center as the half-hot
- Room side (also changed, expected): rooms **33 → 16**; many `Unlabeled space N` removed; added `Mech. Closet (B14)`; 22 detection `room_id` reassignments

### Plan 4 — exact non-room deltas

- Dets/wires/boxes geometry **identical** to golden except:
  - `receptacle.gfci` @ (1369.14, 156.42): `needs_review` **True → False**
  - `receptacle.gfci_240v` @ (1820.82, 296.94): `needs_review` **True → False**
  - `receptacle.gfci_weatherproof` @ (1345.98, 567.42): `needs_review` **True → False**
- Rooms **37 → 15**; Unlabeled pockets gone; added `Mech. Closet (B14)`; 25 room reassignments

## Hecho

- Re-ran diff; status updated; **no golden rewrite**
- A3 message `refresh-golden-mech-b14` ack’d: same plan3 classify blocker they noted

## Cómo probarlo

```bash
uv run python eval/scripts/diff_golden_vs_current.py
uv run pytest engine/tests/eval/test_golden.py -q
```

## Siguiente

Refresh goldens when plan3 half-hot is restored (A2) **or** Santiago allows absorbing that + plan4 `needs_review` into the snapshot.

## Bloqueos

Plan 3 missing `afci_half_hot` @ (895.8, 505.68).

## Decisions

Strict gate: any det/wire/box content change (including `needs_review`) blocks refresh unless Santiago widens the rule.

## Needs from Santiago

OK to absorb plan3 half-hot loss + plan4 `needs_review` flips, or wait for A2?

## Explicación para Santiago

Volví a comparar el motor actual con el golden v0.6.4. En planos 1 y 2 solo
cambian cuartos (regla Mech. Closet B14 / sin Unlabeled). En el **plan 3** sigue
faltando un tomacorriente half-hot en la cocina (~896, 506) y con eso una caja y
cables. En el **plan 4** las marcas son las mismas pero tres receptáculos pasan
`needs_review` de sí a no. Por eso **no actualicé** el golden: el candado pedía
que detecciones/cables/cajas fueran iguales salvo el cuarto.
