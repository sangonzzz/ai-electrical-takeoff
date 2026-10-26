# To Agente 1 — bump PIPELINE_VERSION patch (nm_14_3 travelers)

## Ready

Agente 8 landed 3-way traveler detection → `nm_14_3`:

- `_is_three_way` honors subtypes **and** legend codes `3` / `3D`
- Dedicated dash-graph BFS between distant 3-way gangs (traveler window 1.5–14 pt)
- Plan 1: ≥1 `nm_14_3` (laundry↔entry); Plan 4: 2 travelers
- Tests green in `engine/tests/bom/test_wires.py`

## Please

Bump **patch** of `PIPELINE_VERSION` in `takeoff_engine/__init__.py` (and package version if you keep them in sync). Wire/BOM output shape unchanged; cable_type labeling improved so caches/clients should re-run.

## Smoke

```text
plan1: runs=13 nm_14_3=1
plan4: runs=45 nm_14_3=2
```
