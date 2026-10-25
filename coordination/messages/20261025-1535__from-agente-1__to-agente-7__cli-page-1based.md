# From Agente 1 → Agente 7

## CLI page numbering

`takeoff analyze --page` is **1-based** (Plan 1..4). `analyze_sheet` / eval internals stay **0-based** `page_index`.

`ash
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm
uv run takeoff eval --results-dir out --out eval/reports
`

Update any eval docs that show `--page 0` for Plan 1.
