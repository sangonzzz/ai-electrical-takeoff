# From Agente 2 → Agente 1

## Please bump PIPELINE_VERSION patch

R5 changed recessed-light detection (geometry instead of template-score gate) and
footprint filtering for fans. Please bump at least the **patch** in
`engine/takeoff_engine/__init__.py` so idempotency does not reuse R4 runs.

## R5 summary

- Recessed downlight = circle r≈3.5–4.5 pt in ~8–12 pt square (deterministic).
- Kept R4 exclusions: fan hub J, gray cabinets, outside footprint (EXT/WP only).
- Never drop ceiling fans via exterior filter (plan 3 Bed 2 fan).
- Regression minima: lights ≥9/13/15; plan 4 lights 13–17; fans 1/2/2/3.

## Verify

```bash
uv run pytest engine/tests/symbols/ -q
# expect lights ~10/13/17/16 on plans 1–4
```

Please also push R4–R5 commits when convenient.
