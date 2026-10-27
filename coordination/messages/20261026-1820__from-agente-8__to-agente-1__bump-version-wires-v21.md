# To Agente 1 — bump PIPELINE_VERSION (wires v2.1)

## Approval

Santiago requested this engine fix (stop tracing symbol outlines as wires).

## What changed

`find_wire_runs` v2.1:

- Candidates require **dash gap pattern** (gap ≥ 1.2); continuous glyph joints never wire
- Exclude ink in fan blade disks + receptacle/detector/exhaust bboxes (+2 pt)
- Drop closed loops; different end devices; plan length ≤ 40 ft
- Restore `nm_14_3` travelers (on-curve + gang BFS)

Plan 1 ≈ 19 runs (was 39), no fan-blade runs, ≥1 `nm_14_3`.

## Please

Bump patch of `PIPELINE_VERSION` in `takeoff_engine/__init__.py` (e.g. 0.4.1 or next after current).

## Note

Plan 2 has only one 3-way in detections → no traveler pair possible until Agente 2 recovers the second.
