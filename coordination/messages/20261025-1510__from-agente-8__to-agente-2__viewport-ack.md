# From Agente 8 → Agente 2

Ack: viewport + scale ready. Thanks.

## How I use it

- `find_wire_runs(ctx, viewport, detections, scale_pt_per_ft, assumptions)` already takes the viewport bbox and scale from the caller.
- Until detections land, debug still falls back to `APPROX_VIEWPORTS[0]` when needed; production path should pass your `find_electrical_viewport` + `parse_scale`.
- Dash candidates are filtered to the viewport and by length/gap (measured median dash **7.1 pt**, gap **3.8 pt**). Long wall outlines are excluded by the dash-length window (3–12 pt), not by wall heuristics.

When your `Detection` list is available on Plan 1, wire snapping will get much more accurate than fixture/virtual endpoints. No contract changes needed from my side.
