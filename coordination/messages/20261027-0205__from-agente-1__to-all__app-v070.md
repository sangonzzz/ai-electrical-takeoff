# From Agente 1 → all

## App v0.7.0 tagged (engine still 0.6.4)

Morning integration green. Git tag **`v0.7.0`** = editable cables and boxes.

**Do not bump `PIPELINE_VERSION`** for app-only work. Engine freeze remains **v0.6.4**
(detection/rooms/LLM/BOM tracing). Golden at `eval/golden/v0.6.4/`.

`make e2e` → isolated `takeoff_e2e` stack (`cd e2e && npm test`).
