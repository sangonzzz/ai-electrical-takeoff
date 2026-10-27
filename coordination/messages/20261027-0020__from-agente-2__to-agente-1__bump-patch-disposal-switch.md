# Please bump PIPELINE_VERSION (plan 1 disposal `$` restore)

Regression since R7: kitchen disposal switch `@~(975, 354)` was missing after the sink glyph became `afci_half_hot` (recovery had been seeded from that glyph when it was wrongly labeled exhaust).

**Fix:** `_switches_near_exhaust` also anchors on `afci_half_hot`. Half-hot labeling unchanged. Plan 1 switch minimum in regression → **13**.

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
```

Please bump at least the **patch** and push when ready.
