# From Agente 2 → Agente 7

## Precision pass ready — please re-run eval

Symbol detection rules tightened (fixes 1–8). Geometry still owns coordinates; no LLM for positions.

### How to regenerate / verify

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
# repeat --page 2..4
```

Overlays: `out/debug/detections_p{1..4}.png`  
JSON: `out/plan{1..4}.json`

CLI `--page` is **1-based** (plan number).

### Key counts after the pass (`--no-llm --no-bom`)

| plan | switch | ceiling_fan | light | detector (smoke / smoke_co) |
|------|--------|-------------|-------|------------------------------|
| 1 | 11 | 1 | 10 | 1 / 1 |
| 2 | 10 | 2 | 15 | 2 / 1 |
| 3 | 12 | 2 | 14 | 0 / 2 |
| 4 | 15 | 3 | 14 | 1 / 1 |

Matches Santiago’s visual targets for plan 1 (≈11 sw, 1 fan, smoke+smoke_co) and plan 4 (3 fans).

### Rule summary (see `docs/modules/symbols.md`)

1. Strip dashed wiring before clustering  
2. Switch/receptacle near walls; switch = high `$` IoU  
3. Circle-in-square → recessed light (VP / wall tick subtypes)  
4. Drop keynote tags `^[A-Z]\d{2}$`  
5. Drop porch X markers; exhaust needs half-fill  
6. Ceiling fan = J hub + four blades  
7. Smoke needs SD / SD/MA (orphan SD inside fan bbox OK)

Please re-run the eval suite against these outputs when you can.
