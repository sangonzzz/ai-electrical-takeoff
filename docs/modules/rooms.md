# Rooms module (`engine/takeoff_engine/rooms.py`)

Owner: Agente 3. Builds per-sheet room polygons and assigns detections to rooms.
Every per-room count in the takeoff depends on this module.

## Public API

| Function | Role |
|----------|------|
| `detect_rooms(ctx, viewport, sheet_id) -> list[Room]` | Labels → wall mask → polygons (+ Attic, Exterior) |
| `assign_room(point, rooms) -> room_id \| None` | Point-in-polygon for backend when a user moves a detection |
| `assign_rooms(detections, rooms) -> list[Detection]` | Batch assign; wall-aware; may set `needs_review` |
| `extract_room_labels` / `label_display_list` | Label-only helpers (tests / debugging) |
| `build_wall_mask` / `save_wall_debug_png` / `save_rooms_debug_png` | Raster mask + visual DoD under `out/debug/` |

Callers (Agente 2 pipeline, Agente 5 backend) must pass the **electrical** viewport from
`viewport.find_electrical_viewport` — never the full page.

## Algorithm

### 1. Room labels

1. Take text spans with size in **[9.3, 9.8] pt** whose center lies inside the viewport.
2. **Bold** spans → candidate room labels. Join left-to-right neighbors on the same
   baseline (gap ≤ 8 pt, and the next span must start *after* the previous end — two
   distant `CL` labels on one baseline must not concatenate).
3. Keep a label only if every token is in the SPEC §6 lexicon (or a number / `OPTIONAL` /
   hyphenated `WALK-IN`).
4. Non-bold exact text **`IN ATTIC`** → attic marker (kind `attic` later).
5. **Display names:** must match eval templates (`eval/ground_truth/planN.counts.yaml`).
   Aliases: raw `LNDRY` → display `Laundry` (`Room.name` stays `LNDRY`). Other labels are
   title-cased (`Kitchen / Dining`, `Bedroom / Studio`, `Bath 1`). Repeated raw names get
   suffixes ordered top-to-bottom, left-to-right: `CL 1`, `CL 2`. Unique names stay
   unsuffixed (`Living`).

### 2. Wall mask (~3 px / pt)

1. Rasterize gray wall poché fills (thin rectangles, min side ≤ 12 pt).
2. Rasterize long black strokes (length ≥ 12 pt) thickened ~1.5 pt — wall outlines.
3. **Door closing**
   - Cluster short gray segments that share endpoints → door swing arcs.
   - For door-sized roughly square clusters (~18–55 pt), score each bbox edge against
     existing wall pixels; stroke the best-scoring edge and its opposite to seal the
     opening.
   - Also stroke gray door-leaf fills (thin 24–72 pt rectangles).
4. Morphological **close** with a ~6 pt kernel (small poche leaks only — a door-width
   kernel would merge closets).

Debug: `out/debug/walls_pN.png` (white = barrier, red crosses = labels).

### 3. Regions → room polygons

1. Flood from every **border** free pixel → **exterior** mask. Barrier for rooms =
   walls ∪ exterior. This keeps porch/yard out of interior floods even if a door gap
   remains.
2. Flood-fill from each interior label seed inside that barrier.
3. Labels that land in the **same connected component** (open plan) are grouped.
4. **Open-plan split (reviewers will ask):** split the shared region by **Euclidean
   nearest label** (Voronoi inside the region). We do *not* use geodesic distance along
   free space. Consequences:
   - Boundaries are straight-ish ridges between label points (visible on the overlay).
   - A diagonal cut can cross furniture; we then **fill holes** (contour children) so
     furniture islands stay with the room that owns the surrounding floor.
   - The user can reassign any detection; the boundary is an honest default, not a wall.
5. Attic: gray rectangle around `IN ATTIC` (or a padded box fallback) → room `Attic`
   (`kind=attic`) with **priority** over the room below in `assign_room`.
6. Contours → simplified polygons in PDF points (`approxPolyDP`, ε ≈ 1.5 pt).
7. Synthetic **Exterior** room: `kind=exterior`, empty `polygon` (everything outside the
   building footprint = union of interior/attic polygons for assignment).

Debug: `out/debug/rooms_pN.png` (translucent fills + names on the plan raster).

### 4. Assignment

`assign_room(point, rooms)` priority:

1. Point inside an **attic** polygon → Attic.
2. Point inside one **interior** polygon → that room (if several, smallest area — closet
   over a mis-flooded parent).
3. Else nearest interior within **12 pt** (wall devices whose center sits on the wall).
4. Else if inside the footprint union → nearest interior; else **Exterior**.

`assign_rooms` additionally:

- Biases toward the detection **bbox body** for wall-side preference.
- Sets `needs_review=True` when two rooms are within **4 pt** (ambiguous).

## Parameters (named constants in `rooms.py`)

| Constant | Value | Why |
|----------|-------|-----|
| `_LABEL_SIZE_MIN/MAX` | 9.3 / 9.8 | Bold room labels ~9.5–9.6 pt |
| `_PX_PER_PT` | 3.0 | Raster resolution SPEC §6 |
| `_WALL_SEG_MIN_LEN_PT` | 12 | Skip symbol strokes |
| `_MORPH_CLOSE_PT` | 6 | Seal small poche gaps only |
| `_WALL_ASSIGN_RADIUS_PT` | 12 | Wall-device search (SPEC §6) |
| `_AMBIGUOUS_GAP_PT` | 4 | `needs_review` threshold |
| `_POLY_SIMPLIFY_PT` | 1.5 | Contour simplification |

## Known limits

- Door swings that are not gray short-segment arcs (or whose bbox is atypical) may leave
  a gap; exterior flood still isolates most rooms, but a bad gap can merge two interiors.
- Euclidean open-plan boundaries are not “real walls”; Living / Kitchen / Dining cuts are
  nearest-label defaults.
- Plan 3 (and Plan 4) have **more `CL` labels** inside the electrical viewport than SPEC §1
  lists; we keep every lexicon hit and number them. Message Agente 1 if SPEC should be
  updated.
- Exterior has an empty polygon by contract; “inside Exterior” means “not in any other
  room / outside footprint,” not point-in-polygon on Exterior itself.
- Watermark / note text is excluded by viewport + lexicon, not by a separate OCR filter.

## How to test

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/rooms/ -v
# Inspect out/debug/walls_pN.png and out/debug/rooms_pN.png
```
