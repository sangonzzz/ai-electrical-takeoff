# To Agente 1 — bump PIPELINE_VERSION (wires v3 final)

## Approval

Santiago requested this wires final round (timebox) on the frozen engine.

## What changed

- **Curved-only chains:** reject collinear / low direction-variance dash chains (cabinets, equipment)
- Gap membership around measured ~3.8 pt (`[1.5, 9]`); length collect `[1.5, 12]` (PDF flatten)
- **`nm_14_3` traveler-only:** consecutive 3-way hops or BFS that does **not** graze lights/fans; living/kitchen loop stays `nm_14_2`
- Residual millwork → asked Agente 6 for Wires layer **off by default** + **beta** badge

## Please

Bump at least the **patch** of `PIPELINE_VERSION` in `takeoff_engine/__init__.py`.

## Smoke

```bash
uv run --package takeoff-engine pytest engine/tests/bom/test_wires.py -q
# PNGs: out/debug/wires_plan{1..4}.png
```
