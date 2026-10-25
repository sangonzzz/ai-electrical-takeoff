# From Agente 2 → Agente 4

## `extract_legend` ready

```python
from takeoff_engine.pdf_context import load_page
from takeoff_engine.legend import extract_legend, legend_templates

ctx = load_page("data/plans/escondido_plans.pdf", page_index)  # 0..3
entries = extract_legend(ctx)          # list[LegendEntry], rules already filled category/subtype
templates = legend_templates(ctx, entries)  # entry_id -> LegendTemplate (segments/fills)
```

## What you get

- Electrical LEGEND only (skips `FLOOR FINISH LEGEND`).
- Plumbing (CW/HW/HB/SOV) and attic access panel **omitted**.
- Wiring row omitted (not a countable component).
- Plan 1: ≥25 entries including ceiling_fan, recessed downlight, single_pole switch, GFI receptacle, smoke/CO.
- `interpreted_by="rules"`; your `interpret_legend(entries, legend_png)` can refine category/subtype/codes.
- `symbol_bbox` is the glyph box (left of the description). Codes like `3D`, `GFI`, `VP`, `+84` are in `codes`.

## Templates

`LegendTemplate` has `bbox`, `segments`, `fills` — same vector primitives as on the plan, for raster matching in classify. You do **not** need templates for LLM interpret; just the `LegendEntry` list + a PNG crop of the legend region if useful.
