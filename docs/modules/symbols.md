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

## Candidates (`find_candidates`)

1. Keep black segments/fills whose bbox overlaps the viewport.
2. Drop **walls**: axis-aligned strokes ≥22 pt, or shorter AA strokes hugging gray wall poché.
3. Drop **wiring**: chains of short (2–12 pt) dashes linked by endpoint gap ≤4.5 pt — but **keep** compact dense chains (ceiling fan / light circles): aspect <2.2 with density >0.08, or near-square ≥40 pt.
4. Drop **keynotes**: geometry under `A01`-style tags.
5. Cluster remaining ink with bbox gap < `SYMBOL_CLUSTER_GAP_PT` (1.0). Second pass merges large neighbors (gap 3 pt) so fan blades stay one blob.

## Classify (`classify_candidates`)

1. Rasterize candidate and each legend template at 2 px/pt, same physical size (no rescale).
2. Dilate masks (k=2) and score IoU at rotations 0/90/180/270.
3. Hard size gate: area ratio >4 or max-side ratio >3 → score 0 (stops fan↔switch confusion).
4. Hard prior: near-square cluster ≥70 pt with ≥40 segments → `ceiling_fan` (SPEC §2 #5).
5. Attach code tokens within `CODE_TEXT_RADIUS_PT` (14); refine subtype per SPEC §2 priority.
6. NMS: same category within 8 pt → keep highest confidence.
7. Drop `junction_box` whose center lies inside a `ceiling_fan` bbox.
8. `needs_review` when best <0.22 or top-two within 0.05.

## Pipeline (`analyze_sheet`)

`load_page → viewport/scale → legend (+ optional interpret_legend) → candidates → classify → optional adjudicate → detect_rooms/assign_rooms → optional wires/boxes`. `NotImplementedError` / teammate failures become `warnings`. CLI: `uv run takeoff analyze data/plans/escondido_plans.pdf --page 0 --out out/plan1.json --debug`.

## Known limits

- Assumes sheet cells are framed by long black strokes (true for Escondido PAADU sheets).
- Title must appear as a single bold span containing `ELECTRICAL PLAN`.
- Legend description ownership can still slip on unusually tight rows; rules cover the Escondido set.
- Candidate clustering is O(n²); Plan 3–4 take ~20 s. False positives remain (extra switches/lights); LLM adjudication + eval iteration are the next accuracy lever.
- Fan-coil legend glyph sometimes extracts as a thin sliver and is skipped by the min-side gate.
