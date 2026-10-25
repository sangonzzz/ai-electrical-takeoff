# Symbol engine (Agente 2)

Geometry decides **where**; the legend decides **what**. Plans are vector — positions must be exact. Claude never returns coordinates.

## Modules

| File | Role |
|------|------|
| `viewport.py` | Electrical plan cell + scale (pt/ft) |
| `legend.py` | Legend rows → `LegendEntry` + templates (M2) |
| `symbols.py` | Candidate clusters inside viewport (M3) |
| `classify.py` | Template match + code tokens → `Detection` (M3) |
| `pipeline.py` | `analyze_sheet` orchestration (M4) |

## Viewport (`find_electrical_viewport`)

1. Find bold horizontal span matching `ELECTRICAL PLAN` (size ≥ 18 pt), ignore `ELECTRICAL NOTES`.
2. Collect long **black** vertical segments that have ≥ 200 pt of length **above** the title. (Plan 4: a divider at x≈1439 only exists *below* the title; ignoring it keeps the wide electrical cell.)
3. Cell left/right = nearest such verticals on either side of the title bbox.
4. Cell top = nearest long horizontal above the title that overlaps the cell x-range (else ~20 pt margin).
5. Viewport bottom = `title.y0`. Inset 2 pt from the frame.

### Thresholds

| Name | Value | Why |
|------|-------|-----|
| `_TITLE_MIN_SIZE_PT` | 18 | Title is ~24.9 pt; body text is ~9.6 |
| `_MIN_FRAME_LENGTH_PT` | 400 | Sheet cell edges are hundreds of pt long |
| `_MIN_VERT_ABOVE_TITLE_PT` | 200 | Must actually bound the drawing above the title |
| `_CELL_INSET_PT` | 2 | Keep the frame stroke outside the analysis clip |
| `_AXIS_TOL_PT` | 1.5 | Flattened vectors are not perfectly axis-aligned |

## Scale (`parse_scale`)

Reads `SCALE: 1/4" = 1'-0"` under the title → `(draw_inches / real_feet) * 72` = **18.0 pt/ft**. Fallback: `DEFAULT_PT_PER_FT` (18.0) with a warning.

## Legend (`extract_legend`)

1. Find bold span whose text is exactly `LEGEND` (reject `FLOOR FINISH LEGEND`).
2. Region = sheet cell around the title, down through the attic-access label.
3. Cluster black segments/fills (gap < 1.5 pt); drop long underlines (>40 pt) and oversized blobs.
4. For each symbol blob, collect ~9.6 pt description text in a vertical band between same-column peers (and below the blob for large symbols like the ceiling fan).
5. Attach ~6.5 pt code tokens nearest to that symbol (closest-peer filter).
6. `map_description` → category/subtype; exclude plumbing, attic access, wiring.

### Thresholds

| Name | Value | Why |
|------|-------|-----|
| `_SYMBOL_GAP_PT` | 1.5 | Same as plan clustering; `$` bar may not share endpoints |
| `_DESC_LINE` window | symbol ± peers | Inter-row gaps ≈ multi-line gaps (~8–12 pt) |
| `_CODE_RADIUS_PT` | 28 | Codes sit above/beside the glyph in the legend |
| `_MAX_SYMBOL_*` | 130 pt | Ceiling fan ~116 pt; attic panel / rules are larger or excluded by text |

`legend_templates` returns `LegendTemplate(entry_id, bbox, segments, fills)` for 1:1 raster matching.

## Candidates / classify

*(Filled in M3.)*

## Known limits

- Assumes sheet cells are framed by long black strokes (true for Escondido PAADU sheets).
- Title must appear as a single bold span containing `ELECTRICAL PLAN`.
- Legend description ownership can still slip on unusually tight rows; rules cover the Escondido set.
