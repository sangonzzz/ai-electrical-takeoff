# Please bump PIPELINE_VERSION (R7b — final engine fix)

Plan 1 IN ATTIC circle-with-cross light was still missing from `analyze_sheet(..., use_llm=False)` because `_attic_boxes` used a padded label that swallowed the hallway can above the panel.

**Fix** (Agente 2): detect the gray-stroke rectangle for the attic panel; emit the circle-ring light @~(1117.4, 435.8) with room Attic.

```bash
uv run pytest engine/tests/symbols/test_attic_and_halfhot_r7.py -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
# expect a light with notes attic_panel_light + room Attic
```

Please bump at least the **patch** on `PIPELINE_VERSION` and push when ready.
