# From Agente 2 → Agente 1

## Engine freeze (Agente 2)

Symbol engine final pass before freeze. Please:

1. **Bump PIPELINE_VERSION patch** in `engine/takeoff_engine/__init__.py`
2. **Push** A2 commits (R4–R5 + this freeze pass)
3. Treat `engine/takeoff_engine/{viewport,legend,symbols,classify,pipeline}.py` as **frozen** unless Santiago asks for more

## This pass

- Wall `AFI`/`AFCI` receptacles: keep when rooms mis-label Exterior; text-anchor recovers mega-swallowed duplexes (plan 3 Bed 2 + all plans — 0 orphan AFI tokens)
- Exhaust vs light cross-NMS: Bath 2 no longer double-marks the same half-disc
- Regression still green (plan 3 light floor ≥13 after dedupe)

## Verify

```bash
uv run pytest engine/tests/symbols/ -q
# plan3: 15 AFI receptacles, 4 exhaust, 13 lights, 2 fans
```
