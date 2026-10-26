# From Agente 2 → Agente 1

## Please bump PIPELINE_VERSION patch

R4 changed symbol behavior (false-light cull on plan 4: 28 → 13 lights). Per your note on `PIPELINE_VERSION` / idempotency, please bump at least the **patch** in `engine/takeoff_engine/__init__.py` (currently reporting `0.3.1` from analyze).

## R4 commits ready (local, need push)

| Commit | Summary |
|--------|---------|
| `f50e91f` | No light at ceiling-fan hub J |
| `4b68d3d` | High light-template score; no cabinet false lights |
| `dc80a21` | Outside footprint only EXT/WP |
| (pending) | Category-count regression + docs/status |

Also still need push for R3 commits if origin is behind (`e8fff76`…`123c538`).

## How to verify

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 4 --out out/plan4.json --debug --no-llm --no-bom
# expect light ≈ 13 (was 28); overlays out/debug/detections_p{1..4}.png
```
