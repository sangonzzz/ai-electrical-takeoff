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

`legend_templates` returns `LegendTemplate(entry_id, bbox, segments, fills)` for 1:1 raster matching.

## Candidates (`find_candidates`)

Order matters: remove non-symbol ink **before** clustering so dashes never join a switch or hide a recessed light.

1. Keep black segments/fills whose bbox overlaps the viewport.
2. Drop **walls**: axis-aligned strokes ≥22 pt, or shorter AA strokes hugging gray wall poché.
3. Drop **dashed wiring**: short open polylines (~3–12 pt) that chain along a smooth curve with regular gaps (~1.2–6 pt). Continuous glyph strokes are protected.
4. Drop **keynotes**: geometry under `^[A-Z]\d{2}$` tags (A01, B14, …).
5. Cluster remaining ink with bbox gap < 1.0 pt; second pass merges large neighbors (gap 3 pt).

## Classify (`classify_candidates`)

1. Rasterize candidate vs legend templates at 2 px/pt; dilated IoU at 0/90/180/270.
2. Hard size gate + shape priors.
3. **Precision rules** (rounds 1–2, visual review of all 4 Escondido pages):

| Rule | Behavior | Why |
|------|----------|-----|
| Dashed wiring (R1) | Strip before clustering | Prevented 34 fake switches on dashed curves |
| Switches / receptacles | Center ≤8 pt of wall mask; switch `$` IoU ≥0.45 | Wall devices only |
| Recessed lights | Circle-in-square → `recessed` (`VP` / wall-tick refine) | Recover living-room cans |
| Keynotes / porch X | Drop | Were `smoke_co` / false devices |
| Junction box (R2.1) | **Only** small circle with `J` inside, not a fan hub. Template-only JBs dropped | 5–10 false JBs per plan |
| Detectors (R2.2) | Every viewport `SD` / `SD/MA` → center-dot fill within ~12 pt above/beside. `SD/MA`→`smoke_co`, `SD`→`smoke` | Plan 4 missed bedroom/hallway SDs |
| Exterior light (R2.3) | `EXT` token → `exterior_wall` glyph beside it | Plan 4 porch EXT |
| Exhaust (R2.4) | Half-disc fill **without** duplex slots; `IAQ`→`indoor_air_quality` | Plan 1 bath exhaust; duplex ≠ exhaust |
| Half-hot (R2.5) | Half-disc fill **with** exactly two duplex slots → `afci_half_hot` | Plan 1 kitchen; fill-less template hits dropped |
| Cross NMS (R2.6) | Overlapping light+detector → keep detector; half-hot beats exhaust | Plan 1 recessed-on-SD/MA |
| Wall light (R2.7) | Elongated circle+cross+tick, arc-heavy, no square → `wall` | Plan 1 bath vanity |
| Ceiling fan | `J` hub + four blades | No door/cabinet fans |
| IN ATTIC (R2.8) | Attic panel edges join wall mask; relax switch IoU inside panel; nudge centers into Attic | Spec: attic devices → room Attic |

4. NMS same category 8 pt; then cross-category NMS for known collisions.
5. `needs_review` when best <0.22 or top-two within 0.05.

### Duplex vs exhaust half-fill

Both use a black semicircle fill. Distinction: a **duplex** has exactly two parallel short interior slots; a **circle** outline leaves four edge chords — those are exhaust/IAQ, not half-hot.

### Rough counts after R2 (`--no-llm --no-bom`)

| plan | sw | fan | light | rec | exhaust | detector | JB | notes |
|------|----|-----|-------|-----|---------|----------|----|-------|
| 1 | ~12 | 1 | ~9 | ~26 | 2 (IAQ+bath) | 2 | 0 | wall vanity, HH kitchen, attic light+switch |
| 4 | ~15 | 3 | ~14 | ~39 | 2+IAQ | 5 | 0 | EXT + all SD/SD/MA |

## Pipeline (`analyze_sheet`)

`load_page → viewport/scale → legend → candidates → classify → rooms → optional wires/boxes`.

```bash
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
# --page is 1-based; overlays in out/debug/detections_p{1..4}.png
```

## Known limits

- Sheet cells framed by long black strokes (Escondido PAADU).
- Clustering O(n²); dense sheets ~20 s.
- Receptacle counts still high vs a strict visual count.
- Attic switch centers may be nudged a few pt inward so room assign hits Attic.
