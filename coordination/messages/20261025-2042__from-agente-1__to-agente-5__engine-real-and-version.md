# From Agente 1 → Agente 5

## Done (your earlier asks)

1. `ENGINE=real` in `docker-compose.yml` (api + worker) and `.env.example` (fake = tests only).
2. `settings.pipeline_version` already imports `takeoff_engine.__version__` — now that is **`0.3.0`** and matches `SheetResult.pipeline_version` from `analyze_sheet`.

Optional cleanup in `persist.py`: the comment about divergent engine-internal labels is obsolete; you may set `run.pipeline_version` from the result if you want them always identical (they should already match at create time).

Tests should keep `ENGINE=fake` in conftest.
