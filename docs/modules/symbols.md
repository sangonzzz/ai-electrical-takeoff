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

Order matters: remove non-symbol ink **before** clustering so dashes never join a switch or hide a recessed light.

1. Keep black segments/fills whose bbox overlaps the viewport.
2. Drop **walls**: axis-aligned strokes ≥22 pt, or shorter AA strokes hugging gray wall poché.
3. Drop **dashed wiring** (Fix 1): short open polylines (~3–12 pt, no closure) that chain along a smooth curve with regular gaps (~1.2–6 pt). Continuous glyph strokes (endpoint gap &lt;1.2 pt) are protected so fan blades / light circles are not absorbed into a nearby wire chain.
4. Drop **keynotes** (Fix 4): geometry whose center falls in / candidates that touch a pad around text matching `^[A-Z]\d{2}$` (A01, B14, …) — those tags were false `smoke_co`.
5. Cluster remaining ink with bbox gap &lt; `SYMBOL_CLUSTER_GAP_PT` (1.0). Second pass merges large neighbors (gap 3 pt) so fan blades stay one blob.

### Thresholds (candidates)

| Name | Value | Why |
|------|-------|-----|
| Dash length | ~3–12 pt | Measured dash strokes on Escondido dashed home-runs |
| `_WIRE_GAP_MIN_PT` | 1.2 | Below = continuous symbol stroke |
| Wire gap max | ~6 pt | Typical dash spacing ~2–4.5 pt |
| `_WIRE_CHAIN_MIN` | 2 | Two dashes across a gap already look like wiring |
| Keynote pad | 6 pt | Cover the small rectangle around A01-style tags |

## Classify (`classify_candidates`)

1. Rasterize candidate and each legend template at 2 px/pt, same physical size (no rescale).
2. Dilate masks (k=2) and score IoU at rotations 0/90/180/270.
3. Hard size gate: area ratio &gt;4 or max-side ratio &gt;3 → score 0.
4. **Category rules** (precision pass — visual review of all 4 Escondido pages):

| Rule | Behavior | Why |
|------|----------|-----|
| Switches / receptacles (Fix 2) | Center within ~8 pt of wall mask (gray fills + wall lines). Switch must match the `$` template (S crossing a vertical bar) with IoU ≥ ~0.45 | Dashes and free-field marks were 34→~11 switches on plan 1 |
| Recessed lights (Fix 3) | Every circle-in-square glyph in the viewport → `light`. Default subtype `recessed`; `recessed_vapor_proof` only with a nearby `VP` token; `wall` only with the wall-tick shape | Plan 4 living room missed ~6 of ~10 circles before dash strip + force-light |
| Keynotes (Fix 4) | Reject candidates that contain/touch `^[A-Z]\d{2}$` text or its box | Were classified as smoke_co |
| Porch X markers (Fix 5) | Drop square-with-X at porch/post corners (not in legend) | Not devices |
| Exhaust fan (Fix 5) | Requires a black fill (half-filled circle) | Outline-only hits were false exhausts |
| Ceiling fan (Fix 6) | Requires a `J` token near the hub (≤8 pt of center **or** in the middle third of the bbox) **and** four blade loops (large near-square, enough segments). Template match alone is never enough | Door swings / cabinets must not become fans; plan 4 → 3 fans |
| Smoke / smoke_co (Fix 7) | Circle + center-dot fill + `SD` or `SD/MA` token. `SD/MA` → `smoke_co`, `SD` → `smoke`. Orphan SD tokens inside a fan bbox (or &lt;25 pt of another plan detection) still emit a detector | Bedroom SD drawn inside the fan cluster was missed |
| Junction vs fan | Drop `junction_box` whose center lies inside a `ceiling_fan` bbox | Spec: central J is the fan hub |

5. Attach code tokens within `CODE_TEXT_RADIUS_PT` (14); refine subtype per SPEC §2 priority.
6. NMS: same category within 8 pt → keep highest confidence.
7. `needs_review` when best &lt;0.22 or top-two within 0.05.

### Rough expected counts (visual review)

| Page | switches | ceiling_fan | smoke + smoke_co |
|------|----------|-------------|------------------|
| Plan 1 | ~11 | 1 | 1 + 1 |
| Plan 4 | — | 3 | — |

Re-check overlays: `out/debug/detections_p{1..4}.png` after each fix.

## Pipeline (`analyze_sheet`)

`load_page → viewport/scale → legend (+ optional interpret_legend) → candidates → classify → optional adjudicate → detect_rooms/assign_rooms → optional wires/boxes`. `NotImplementedError` / teammate failures become `warnings`.

CLI page is **1-based** (plan number):

```bash
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
```

## Known limits

- Assumes sheet cells are framed by long black strokes (true for Escondido PAADU sheets).
- Title must appear as a single bold span containing `ELECTRICAL PLAN`.
- Legend description ownership can still slip on unusually tight rows; rules cover the Escondido set.
- Candidate clustering is O(n²); Plan 3–4 take ~20 s.
- Receptacle counts are still high vs a strict visual count; wall proximity helps but legend look-alikes near walls remain.
- Fan-coil legend glyph sometimes extracts as a thin sliver and is skipped by the min-side gate.
