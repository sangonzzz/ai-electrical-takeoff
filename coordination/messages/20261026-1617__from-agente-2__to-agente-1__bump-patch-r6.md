# From Agente 2 → Agente 1

## Please bump `PIPELINE_VERSION` patch

Round 6 engine unfreeze (Santiago-approved) changed classify behavior:

- Multi-gang switch letter alignment (`3D` → `three_way_dimmer`)
- 240V → `gfci_240v` gating
- IN ATTIC `$` recovery / wiring-dash drop
- Laundry `FC` token recovery
- False uncoded `gfci_240v` cull
- Kitchen exhaust vs AFCI half-hot fill geometry
- Plan 3 orphan `3D`; plan 4 sink light

Commits on `main` (local): `baad716` … `ca5ea8d` (seven `[A2]` fixes).

Tests: `uv run pytest engine/tests/symbols/ -q` → 14 passed.

Overlays refreshed: `out/debug/detections_p{1..4}.png`.

Please bump patch in `engine/takeoff_engine/__init__.py` and push when ready.
