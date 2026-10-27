# To Agente 7 — Edit cables testids

New attributes for e2e (fixture mode recommended):

| testid | Where |
|--------|--------|
| `wire-run` | Each cable path group on the plan |
| `wire-run-type-select` | Details panel cable type `<select>` |
| `wire-run-delete` | Delete cable button |
| `wire-create-mode` | Toolbar “New cable” button (visible when Edit cables on) |
| `box-mark` | Each box gang mark |

Flow: turn on **Edit cables** (floating toolbar) → Wires layer on → click `wire-run` →
Details shows type select / delete. **New cable** → click two `detection-mark`s.
Boxes layer → click `box-mark`.
