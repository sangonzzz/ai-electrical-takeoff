# To Agente 1 — bump PIPELINE_VERSION (wires v3.1)

## Approval

Santiago requested this wires final round (v3.1 exact product rules) on the frozen engine.

## What changed

- Dash components + tip attach + chord millwork reject (rules 1–4)
- Cable type: either-end `three_way` / `three_way_dimmer` → `nm_14_3` (rule 5)
- Plan1 regression restored (laundry→kitchen lights, entry→living lights, bath/bed, ≥2 nm_14_3, no B38)
- Plan4 held (~33 runs, 3 nm_14_3)
- Calibrated gap/turn/extend beyond nominal (documented in `docs/modules/bom.md` + `wires.py` header)

## Please

Bump at least the **patch** of `PIPELINE_VERSION` in `takeoff_engine/__init__.py`.

## Smoke

```bash
uv run --package takeoff-engine pytest engine/tests/bom/test_wires.py -q
# PNGs: out/debug/wires_plan{1..4}.png
# Counts: plan1 28/7 nm_14_3, plan4 33/3 nm_14_3
```
