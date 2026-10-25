# From Agente 2 → Agente 5

## Engine entry point ready

```python
from takeoff_engine.pipeline import analyze_sheet

result = analyze_sheet(pdf_path, page_index, use_llm=True, with_bom=True)
# result: SheetResult (sheet, legend, rooms, detections, wire_runs, boxes, warnings, timings_ms, llm_usage)
```

CLI equivalent:

```bash
uv run takeoff analyze data/plans/escondido_plans.pdf --page 0 --out out/plan1.json --no-llm
```

Feature flags: `ENABLE_LLM`, `ENABLE_BOM` (and CLI `--llm/--no-llm`, `--bom/--no-bom`). Without an API key, legend/adjudicate degrade gracefully with warnings.

Sheet ids are UUIDs minted per run; `sheet.viewport` / `scale_pt_per_ft` / `legend_bbox` are filled.
