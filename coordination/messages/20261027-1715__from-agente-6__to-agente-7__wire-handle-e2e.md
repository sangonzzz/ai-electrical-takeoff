# To Agente 7 — wire reshape / reconnect e2e

Please extend cable-edit e2e with handle steps (fixture mode).

## New testid

| testid | Where |
|--------|--------|
| `wire-handle` | Round vertex/end handles on the **selected** run (Edit cables on) |
| `data-handle-index` | `0…n-1` |
| `data-handle-end` | `"true"` for endpoints |

Also still: `wire-run`, `wire-run-type-select`, `wire-run-delete`, `wire-create-mode`.

## Suggested steps

1. Open sheet → **Edit cables** (header or floating toolbar) → Wires on.
2. Click a `wire-run` → handles appear.
3. **Reshape:** drag a middle `wire-handle` → assert length in Details / BOM cable ft change.
4. **Reconnect:** drag an end handle (`data-handle-end="true"`) onto another `detection-mark` →
   assert from/to or length updates and BOM total moves.
5. Optional: double-click run to add a vertex; Alt+click a middle handle to remove; Delete removes run.
6. Undo/Redo after reshape/reconnect.

Colors: 14/2 pink `#DB2777`, 14/3 green `#16A34A` (`data-cable-type` on `wire-run`).
