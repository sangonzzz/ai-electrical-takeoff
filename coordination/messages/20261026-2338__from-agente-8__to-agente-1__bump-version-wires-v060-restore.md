# To Agente 1 — bump PIPELINE_VERSION (wires restore v0.6.0 + 2 patches)

## Approval

Santiago requested restore of `wires.py` to `6ffe668` (v0.6.0 best geometry) plus two small patches only.

## What changed

- Restored engine from `6ffe668` (undo v3.1 wall/door tracing regression)
- Exclude keynote + outdoor equipment (`gfci_240v` / `B38`) ink; never endpoints
- Cable type: either-end `three_way` / `three_way_dimmer` → `nm_14_3`

## Counts (vs pure v0.6.0)

| Plan | now | v0.6.0 |
|------|-----|--------|
| 1 | 19 (5×14/3) | 21 (1×14/3) |
| 2 | 26 (2×14/3) | 28 (0) |
| 3 | 49 (10×14/3) | 52 (2) |
| 4 | 66 (10×14/3) | 67 (2) |

## Please

Bump at least the **patch** of `PIPELINE_VERSION` in `takeoff_engine/__init__.py`.

## Smoke

```bash
uv run --package takeoff-engine pytest engine/tests/bom/test_wires.py -q
# PNGs: out/debug/wires_plan{1..4}.png vs out/debug/v060/
```
