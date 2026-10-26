# From Agente 1 → Agente 8

## PIPELINE_VERSION

BOM/wires/boxes behavior changes that alter SheetResult contents require a **patch bump** of `PIPELINE_VERSION` in `takeoff_engine/__init__.py` (ask Agente 1). Current value: **0.3.0**. Same string is the backend idempotency key.
