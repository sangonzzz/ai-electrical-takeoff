# To Agente 5 — BOM sections for quote PDF

Pricing/SKU update is in `data/price_list.yaml` + `compute_bom` (Agente 8). Analysis/
`PIPELINE_VERSION` unchanged.

## Please wire quote PDF sections

`takeoff_engine.bom.group_bom_lines(bom.lines)` →  
`list[tuple[section_key, label, lines]]` in order:

1. `Devices`
2. `Fixtures (allowance)`
3. `Boxes and plates`
4. `Cable`

In `exports._quote_story_for_bundle`, instead of one flat “Priced materials” table,
emit an `h2`/subheading per non-empty group, then that group’s rows (same columns).
Assumptions already include `pricing_note_240v`, `pricing_note_detector`,
`pricing_note_fixtures` from `assumptions.yaml`.

```python
from takeoff_engine.bom import group_bom_lines

for _key, label, lines in group_bom_lines(bundle.bom.lines):
    story.append(Paragraph(label, styles["h2"]))
    # build table from `lines` …
```

Smoke: any sheet with fans/lights should show **Fixtures (allowance)** separate from
switches/receptacles.
