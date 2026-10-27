# To Agente 6 — Wires layer off by default + beta badge

## Why

Wires final round (curved-only + gap window + `nm_14_3` traveler-only) still leaves **non-wire geometry** on the debug overlays:

- Plan 4 kitchen cabinet / millwork dashes still get pink runs
- Bath sink/toilet dashed outlines can still latch
- Plan 1 B38 outline risk remains in the candidate set on some sheets

Real lighting curves look better and the living/kitchen loop is no longer labeled `nm_14_3`, but false positives are not gone.

## Please

1. **Wires layer OFF by default** in the sheet viewer.
2. Show a **“beta”** badge next to the Wires layer toggle (or in the layer list).
3. Optional tooltip: “Experimental — may include millwork / fixture outlines.”

## Docs

Limit documented in `docs/modules/bom.md` (§ Known limit) and `data/assumptions.yaml` (`wires_layer_beta: true`).

## Evidence

`out/debug/wires_plan{1..4}.png` (regenerated after this round).
