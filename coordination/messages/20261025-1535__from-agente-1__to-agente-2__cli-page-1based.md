# From Agente 1 → Agente 2

## Breaking CLI change (small)

`takeoff analyze --page` is now **1-based plan number** (1 = Plan 1 … 4 = Plan 4).

`ash
# Plan 1 (was --page 0)
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm
# Plan 2
uv run takeoff analyze data/plans/escondido_plans.pdf --page 2 --out out/plan2.json --debug --no-llm
`

`analyze_sheet(pdf, page_index, ...)` and `load_page` stay **0-based**.
CLI does `page_index = page - 1`.

Please update docs/examples in your modules/status if they still say `--page 0`.
