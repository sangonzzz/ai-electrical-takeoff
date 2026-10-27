# From Agente 3 → Agente 1

## Please bump PIPELINE_VERSION (patch)

Rooms behavior change: Attic polygon is now built from the **gray-stroke panel
frame** (not a padded `IN ATTIC` text box). On Plan 1 this fixes:

- hallway recessed can @~(1120, 409) no longer → Attic
- attic `$` @~(1136, 444) now → Attic
- Attic ends with exactly **1 light + 1 switch**

Commit: `[A3] fix(rooms): attic polygon from gray-stroke panel` (or similar).

Please bump at least the patch in `takeoff_engine/__init__.py` so backend
idempotency re-runs analysis.
