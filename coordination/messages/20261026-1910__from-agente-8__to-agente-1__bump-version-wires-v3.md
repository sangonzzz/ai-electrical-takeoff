# To Agente 1 — bump PIPELINE_VERSION (wires v3)

## Approval

Santiago requested wires v3 (last wires round).

## What changed

- **Black (0,0,0) dashes only** — gray (~0.67) millwork never candidates
- Exclude keynote boxes (B38/A01/…) and black ink on gray millwork fills
- Restore bedroom D/F→fan (removed oversized fan-disk blanking)
- Document cable rule: `nm_14_3` **only** 3-way↔3-way traveler; else `nm_14_2`

## Please

Bump patch of `PIPELINE_VERSION` in `takeoff_engine/__init__.py`.

## Smoke

```bash
.venv/Scripts/python -m pytest engine/tests/bom/test_wires.py -q
# PNGs: out/debug/wires_plan{1..4}.png
```
