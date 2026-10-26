# To Agente 1 — bump PIPELINE_VERSION (wires v2)

## Approval

Santiago requested this engine change explicitly (wires v2 rebuild + ask you to bump).

## What changed

`find_wire_runs` rebuilt:

- Full-curve linking (endpoint gap ≤ measured gap × 2 + tangent continuity)
- Ends at nearest device **bbox boundary**
- Mid-path fixture splits; distant 3-way tips → `nm_14_3`
- Debug PNGs: dash underlay + labeled runs

Owned paths only (`wires.py`, tests, bom docs, assumptions, status).

## Please

Bump **at least patch** of `PIPELINE_VERSION` in `takeoff_engine/__init__.py` (currently 0.4.0 freeze — Santiago approved). Suggest **0.4.1** or **0.5.0** if you treat this as minor behavior change.

## Smoke

```bash
.venv/Scripts/python -m pytest engine/tests/bom/test_wires.py -q
# PNGs: out/debug/wires_plan{1..4}.png
```
