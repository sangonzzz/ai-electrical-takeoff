# AI Electrical Takeoff: Technical Spec (source of truth)

Owner: Santiago Gonzalez (GitHub `sangonzzz`). This file is the single source of truth for every agent.
If something here is wrong or missing, do not silently diverge: send a message to Agente 1 (see AGENTS.md).

---

## 0. Goal

Build an application that takes one PDF with 4 residential electrical plans, analyzes each sheet separately with AI,
and returns an electrical takeoff that can be reviewed and corrected directly on the drawing.

Minimum requirements (all mandatory):

1. Load the PDF and split the plans. Each of the 4 sheets is analyzed separately.
2. Detect components with AI: at minimum ceiling fans, lights, switches, receptacles. Each detection stores its type,
   its position on the plan and the room it belongs to.
3. Count per room and per plan: a table with the quantity of each component per room and the home total.
4. Draw every detection on the plan. Every number must trace back to marks on the plan.
5. CRUD on the plan: create (add a missed component), read (type, room, confidence), update (type, position, room),
   delete. Every correction updates per-room counts and totals immediately.

Extra (we WILL do it): bill of materials. Boxes by gang size drawn on the plan, fan-rated boxes, cable by type and
length measured from the dashed wiring lines with a stated routing assumption and drawn on the plan, a priced material
total from a sourced price list, and CRUD that updates boxes, cable and price.

What the reviewers weigh most: visual evidence on the plan (errors shown, not hidden), accuracy on fans and lights,
smart use of the legend and of the plan text, clean architecture, honest limits.

Stack (requested by the team): backend Python + FastAPI, frontend React, async processing with Redis, good practices.

---

## 1. Facts about the input PDF (verified by analysis, use them)

File: `data/plans/escondido_plans.pdf`. 4 pages, each 2592 x 1728 pt (36 x 24 in). Public domain plans
(City of Escondido PAADU program).

| Page | Sheet  | Home               | "ELECTRICAL" word of title "ELECTRICAL PLAN - PLAN N" (x0, y0) | Electrical LEGEND title (x0, y0) |
|------|--------|--------------------|-----------------------------------------------------------------|----------------------------------|
| 1    | A1-111 | Plan 1, studio     | (944, 846)                                                      | (1458, 68)                       |
| 2    | A2-111 | Plan 2, 2 bedrooms | (230, 532)                                                      | (1458, 1069)                     |
| 3    | A3-111 | Plan 3, 2 bedrooms | (904, 846)                                                      | (1458, 68)                       |
| 4    | A4-111 | Plan 4, 3 bedrooms | (1093, 687)                                                     | (1028, 779)                      |

Coordinates are PDF points, origin top-left (PyMuPDF convention). Use these values only as test sanity checks;
the code must find them dynamically (layouts differ per sheet).

Key facts:

- **Fully vector.** No raster plan. Curves are flattened into many short straight segments (median about 2 pt).
  A small circle is about 12 segments, about 8 x 8 pt. Only 2 raster images per page (city logos, ignore).
- **Each sheet has 3 drawings:** "ELECTRICAL PLAN - PLAN N", "MECHANICAL PLAN - PLAN N", "FINISH PLAN - PLAN N",
  plus legend, keynotes and notes. The mechanical plan contains similar-looking symbols (fans, IAQ). Only the
  electrical plan viewport may be analyzed.
- **Styles separate the layers:**
  - Black strokes, color (0,0,0), width 0.24: electrical symbols, dashed wiring, wall outlines, the "S" of switch "$".
  - Black fills: filled parts of symbols (half disc of exhaust fan and of AFCI half-hot receptacle, the dot in smoke detectors).
  - Gray strokes, color (0.67,0.67,0.67), widths 0.24 and 0.72: architecture (doors, door swings, windows, cabinets,
    plumbing fixtures, furniture, attic panel, keynote leader lines).
  - Gray fills (0.75,0.75,0.75) rectangles: wall poché (filled wall bodies).
  - White fills: masks. No optional content layers (OCGs).
- **PyMuPDF gotcha (real bug found):** `page.get_drawings()` returns perfectly horizontal or vertical lines with a
  zero-width or zero-height `rect`. `Rect.intersects()` returns False for empty rects, so filtering drawings by
  `d["rect"].intersects(clip)` silently drops every axis-aligned line (wall outlines, the bar of "$", the two lines
  of receptacles). Always inflate the rect by about 0.5 pt before testing, or test the item points.
- **Text layer is real text.** Room labels are Arial,Bold about 9.5 to 9.6 pt (may be multi-word on one line:
  "KITCHEN / DINING", "BED 1", "OPTIONAL BED 3", "WALK-IN CLOSET"). Device codes are Arial about 6.5 pt, often
  rotated 90 degrees next to wall devices: `D`, `F`, `3D`, `VS`, `A`, `AFI`, `GFI`, `WP`, `240V`, `MW`, `DW`, `H`,
  `FC`, `EXT`, `+84`, `+42"`, `+30"`, `SD`, `SD/MA`, `J`, `IAQ`, `P`, `VP`. Keynote tags in small boxes
  (`A01`, `B14`, `B32`, `B38`, `F03`, ...) are NOT components. "IN ATTIC" (Arial 9.6 regular) marks an attic box.
- **Watermark:** "FOR USE IN THE CITY OF ESCONDIDO" in Arial-BoldMT about 130 pt crosses every sheet. Ignore it.
- **Scale:** each drawing title has `SCALE: 1/4" = 1'-0"` under it. That means 0.25 in = 1 ft, so 18 pt = 1 ft.
  Parse it from the text; do not hardcode (fallback 18.0 with a warning).
- **Room labels inside each electrical plan:**
  - Plan 1: BATH, BEDROOM / STUDIO, CL (x2), KITCHEN / DINING, LIVING, LNDRY
  - Plan 2: BATH, BED 1, BED 2, CL (x2), DINING, HALLWAY, KITCHEN, LIVING, LNDRY
  - Plan 3: BATH 1, BATH 2, BED 1, BED 2, CL (x4 in electrical viewport — verified by rooms), HALL, KITCHEN / DINING, LIVING, LNDRY
  - Plan 4: BATH 1, BATH 2, BED 1, BED 2, CL (x2 in electrical viewport — verified by rooms), HALLWAY, KITCHEN, LIVING, LNDRY, OPTIONAL BED 3, WALK-IN CLOSET
  (Verify counts of CL per plan in code; bold text outside the viewport, like notes, must be excluded.
   Repeated CL labels get display names CL 1, CL 2, … ordered L→R, T→B.)
- **Open plan areas:** Living, Kitchen and Dining are often one open space with no walls between labels.
- **Legend content (same on all 4 sheets, but read it per sheet):**
  - Switches ("$"): plain = single pole; `3D` = three-way dimmer; `VS` = vacancy sensor; `D` = dimmer; `F` = fan;
    `A` = astronomical time or motion sensor switch. (The assessment says a `3` means 3-way; support `3` too.)
  - Exhaust fan (half filled circle); IAQ = indoor air quality fan.
  - Pendant light high-efficacy (`P`); wall mounted high-efficacy light; exterior wall mounted light with photo sensor
    (`+84 EXT`); recessed high-efficacy downlight; recessed downlight vapor proof (`VP`).
  - Smoke detector (`SD`); combination smoke/carbon monoxide (`SD/MA`); electrical junction box (circle with `J`).
  - Ceiling fan: large 4-blade symbol with a `J` circle at its center ("CEILING FAN OPTIONAL (PRE WIRE FOR CEILING FAN ONLY)").
  - Electrical wiring: dashed curved line.
  - Receptacles (duplex outlet): `AFI` (AFCI); `GFI 240V` (240 volts); `GFI`; `GFI WP` (weatherproof);
    AFCI half hot (half filled symbol); `GFI MW` (microwave); `GFI DW` (dishwasher); `H` (range hood);
    `FC` in a rectangle (dedicated outlet for fan coil unit).
  - Not electrical components (exclude): CW, HW, HB, SOV HB (plumbing), attic access panel (rectangle with diagonals).

---

## 2. Taxonomy and counting rules

Detections use `category` + `subtype` (strings below). Count keys are `category` and `category.subtype`.

```
ceiling_fan : ceiling_fan, fan_light
light       : recessed, recessed_vapor_proof, pendant, wall, exterior_wall
switch      : single_pole, three_way, three_way_dimmer, dimmer, fan, vacancy_sensor, astronomical_timer
receptacle  : duplex, afci, afci_half_hot, gfci, gfci_weatherproof, gfci_240v, gfci_microwave,
              gfci_dishwasher, range_hood, fan_coil_dedicated, 240v
exhaust_fan : bath_exhaust, indoor_air_quality
detector    : smoke, smoke_co
junction_box: junction_box
```

All code tokens found next to a symbol are also stored in `codes` (e.g. `["WP","GFI","240V"]`), and a mounting
height like `+42"` goes to `mount_height_in`. Receptacle subtype priority when several codes apply:
`240V` > `MW` / `DW` / `H` / `FC` > `WP` > half-hot > `GFI` > `AFI` > plain duplex.

Counting rules (from the assessment, plus our stated assumptions; keep in `coordination/DECISIONS.md`):

1. Kitchen and Dining are separate rooms only when the plan labels them separately (Plan 2: yes; Plans 1 and 3:
   one room "Kitchen / Dining").
2. A component outside the building footprint counts under the room "Exterior" (porch light, WP receptacle,
   outdoor heat pump receptacle).
3. A combined fixture counts once under its combined type (fan/light, smoke/CO).
4. Switch type follows the letter next to the switch symbol, as defined by that sheet's legend and notes.
5. Assumption: the ceiling fan symbol includes a `J` circle at its center. It counts as ONE ceiling fan, not as a
   ceiling fan plus a junction box. A standalone `J` circle is a junction box.
6. Assumption: devices inside the "IN ATTIC" box belong to a room "Attic" (kind `attic`).
7. Assumption: open-plan boundaries between labels are split by nearest label (see rooms algorithm). The boundary
   is drawn on the plan and the user can reassign any detection.
8. Repeated labels get a suffix in display name: "CL 1", "CL 2" (ordered left to right, top to bottom).
9. Only the electrical plan viewport is analyzed; mechanical and finish plans are excluded.

---

## 3. Architecture and repo layout

```
ai-electrical-takeoff/
  AGENTS.md                      shared rules for agents (do not edit except Agente 1)
  docs/SPEC.md                   this file
  docs/architecture.md           diagrams (Mermaid) + data flow (Agente 1, final)
  docs/design-doc.md             written by Santiago at the end
  docs/modules/<module>.md       one per module, by its owner
  coordination/
    DECISIONS.md                 counting rules and assumptions (Agente 1 owns; others request changes)
    status/agente-N.md           each agent owns its own file
    messages/                    one NEW file per message (never edit someone else's file)
  contracts/
    schema.json                  JSON Schema exported from engine models (generated)
    fixtures/sheet_result.sample.json        realistic sample for Plan 1 (hand-made by Agente 1)
    fixtures/takeoff.sample.expected.json    expected counts for that sample
  engine/                        Python package `takeoff_engine` (pure, no web)
    takeoff_engine/
      models.py                  Pydantic contracts (Agente 1)
      types.py                   internal shared dataclasses: PageContext, Candidate, Adjudication (Agente 1)
      takeoff.py                 compute_takeoff() pure function (Agente 1)
      config.py                  settings and thresholds (Agente 1)
      pdf_context.py             page loading, styled primitives, words/spans (Agente 1, implemented in scaffold)
      viewport.py                find electrical viewport + scale (Agente 2)
      legend.py                  extract legend entries geometry + text (Agente 2)
      symbols.py                 candidate symbol clusters (Agente 2)
      classify.py                legend template matching + code tokens (Agente 2)
      pipeline.py                orchestration analyze_sheet() (Agente 2)
      rooms.py                   room polygons, footprint, assignment (Agente 3)
      llm/                       Claude client, prompts, cache, tasks (Agente 4)
      wires.py, boxes.py, bom.py, pricing.py   bill of materials (Agente 8)
      overlay.py                 static PNG/PDF overlays for debugging and reports (Agente 7)
      cli.py                     `takeoff` CLI (Agente 1 skeleton, Agente 2 owns analyze, Agente 7 owns eval).
                                 CLI `--page` is plan number 1..4; `page_index` in APIs/models stays 0-based.
    tests/                       pytest, one folder per module owner
    prompts/                     versioned prompt files (Agente 4)
  backend/                       FastAPI app + ARQ worker + SQLAlchemy + Alembic (Agente 5)
  web/                           React + TypeScript + Vite (Agente 6)
  eval/                          ground truth, eval reports (Agente 7)
  data/plans/escondido_plans.pdf
  data/price_list.yaml           sourced prices (Agente 8)
  data/assumptions.yaml          BOM routing assumptions (Agente 8)
  docker-compose.yml, Makefile, .env.example, .github/workflows/ci.yml   (Agente 1)
```

Technology choices (and why, for the design doc):

- Python 3.12, `uv` for dependency management (fast, lockfile). `engine` and `backend` are packages in one uv workspace.
- PyMuPDF: exact access to vector paths and text of the PDF, plus rendering. NumPy, OpenCV (headless), Shapely 2:
  geometry, rasterized matching, polygons.
- Anthropic SDK (Claude) with tool use / structured output validated by Pydantic: legend understanding and
  adjudication of ambiguous symbols. Default model from env `ANTHROPIC_MODEL` (default `claude-sonnet-5-5`),
  cheap model `ANTHROPIC_MODEL_CHEAP` (default `claude-haiku-5-5`).
- FastAPI + Pydantic v2, SQLAlchemy 2 async + asyncpg, Alembic, PostgreSQL 16.
- Redis 7 + ARQ (asyncio job queue, fits FastAPI async): durable background analysis jobs with retries.
- React + TypeScript + Vite, pnpm, TanStack Query (server state, optimistic updates), Zustand (UI state),
  react-zoom-pan-pinch (pan/zoom), Tailwind CSS, lucide-react icons, Vitest.
- Docker Compose for the whole stack. GitHub Actions CI (ruff, pytest, web typecheck + build + vitest).

Why hybrid detection instead of "send the image to a vision model": the plans are vector, so positions can be exact.
Vision LLMs are imprecise with coordinates, miscount dense symbols, are non-deterministic and cost more. We use
geometry for WHERE and the legend + Claude for WHAT. Claude never returns coordinates.

---

## 4. Contracts (engine/takeoff_engine/models.py)

All coordinates are PDF points in page space, origin top-left. One sheet = one page.

```python
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0.0"

class Category(StrEnum):
    CEILING_FAN = "ceiling_fan"; LIGHT = "light"; SWITCH = "switch"; RECEPTACLE = "receptacle"
    EXHAUST_FAN = "exhaust_fan"; DETECTOR = "detector"; JUNCTION_BOX = "junction_box"

SUBTYPES: dict[str, list[str]] = { ... exactly as in section 2 ... }

class Point(BaseModel): x: float; y: float
class BBox(BaseModel): x0: float; y0: float; x1: float; y1: float

class Evidence(BaseModel):
    legend_entry_id: str | None = None
    match_score: float | None = None        # 0..1 similarity to the legend symbol
    text_tokens: list[str] = []             # tokens found near the symbol
    llm_label: str | None = None
    llm_reason: str | None = None
    notes: list[str] = []

class Detection(BaseModel):
    id: str                                  # uuid4
    sheet_id: str
    category: Category
    subtype: str
    codes: list[str] = []
    mount_height_in: float | None = None
    center: Point
    bbox: BBox
    rotation_deg: Literal[0, 90, 180, 270] = 0
    room_id: str | None = None
    room_source: Literal["auto", "manual"] = "auto"
    confidence: float = Field(ge=0, le=1)
    source: Literal["geometry", "llm", "user"]
    status: Literal["active", "deleted"] = "active"
    needs_review: bool = False
    evidence: Evidence = Evidence()

class Room(BaseModel):
    id: str
    sheet_id: str
    name: str                                # raw label text, e.g. "KITCHEN / DINING"
    display_name: str                        # e.g. "Kitchen / Dining", "CL 2", "Exterior", "Attic"
    kind: Literal["interior", "exterior", "attic"]
    polygon: list[Point]                     # exterior ring, empty for "Exterior" (it is everything outside the footprint)
    label_point: Point | None = None
    source: Literal["auto", "manual"] = "auto"

class LegendEntry(BaseModel):
    id: str
    description: str                         # text from the legend row
    codes: list[str] = []                    # code tokens printed with the legend symbol
    category: Category | None = None
    subtype: str | None = None
    combined: bool = False
    symbol_bbox: BBox
    interpreted_by: Literal["rules", "llm"] = "rules"

class WireRun(BaseModel):
    id: str
    sheet_id: str
    points: list[Point]                      # polyline following the dashed line
    from_detection_id: str | None
    to_detection_id: str | None
    cable_type: Literal["nm_14_2", "nm_14_3"]
    plan_length_ft: float
    vertical_allowance_ft: float
    total_length_ft: float
    confidence: float
    source: Literal["geometry", "user"]

class Box(BaseModel):
    id: str
    sheet_id: str
    center: Point
    bbox: BBox
    kind: Literal["device", "fan_rated", "ceiling_round", "none"]
    gangs: int                               # 1, 2, 3...
    detection_ids: list[str]
    cover: Literal["plate", "weatherproof_cover", "none"]
    source: Literal["geometry", "user"]

class SheetImage(BaseModel):
    url: str | None = None                   # filled by backend
    dpi: int
    origin: Point                            # viewport top-left in PDF points
    width_px: int
    height_px: int

class Sheet(BaseModel):
    id: str
    document_id: str | None = None
    page_index: int                          # 0-based
    sheet_number: str | None = None          # "A1-111"
    title: str | None = None                 # "ELECTRICAL PLAN - PLAN 1"
    page_width: float
    page_height: float
    viewport: BBox
    legend_bbox: BBox | None = None
    scale_pt_per_ft: float
    image: SheetImage | None = None

class LlmUsage(BaseModel):
    calls: int = 0; input_tokens: int = 0; output_tokens: int = 0; cost_usd: float = 0.0; cache_hits: int = 0

class SheetResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    pipeline_version: str
    sheet: Sheet
    legend: list[LegendEntry]
    rooms: list[Room]
    detections: list[Detection]
    wire_runs: list[WireRun] = []
    boxes: list[Box] = []
    warnings: list[str] = []
    timings_ms: dict[str, float] = {}
    llm_usage: LlmUsage = LlmUsage()

class TakeoffRow(BaseModel):
    room_id: str; room_name: str; counts: dict[str, int]     # keys: "light" and "light.recessed", etc.

class Takeoff(BaseModel):
    sheet_id: str; rows: list[TakeoffRow]; totals: dict[str, int]; unassigned: dict[str, int]

class BomLine(BaseModel):
    item_key: str; description: str; quantity: float; unit: str
    unit_price: float | None; extended_price: float | None; price_source: str | None
    source_ids: list[str] = []               # detection / box / wire ids behind this line

class Bom(BaseModel):
    sheet_id: str; lines: list[BomLine]; total_usd: float; assumptions: dict[str, float | str]
```

`compute_takeoff(rooms, detections) -> Takeoff` lives in `takeoff.py`, ignores `status == "deleted"`, and is the
only counting logic. The frontend mirrors it in `web/src/lib/takeoff.ts`; both are tested against
`contracts/fixtures/takeoff.sample.expected.json`.

Contract changes: only Agente 1 edits `models.py`, regenerates `contracts/schema.json` and the TS types
(`web/src/types/contracts.ts`), and announces it in `coordination/messages/`.

---

## 5. Engine pipeline (symbols)

`analyze_sheet(pdf_path, page_index, *, use_llm=True) -> SheetResult`, steps and owners:

1. **pdf_context (A1, ready in the scaffold):** load page, collect drawings with the inflated-rect fix, split into
   styled primitives: black segments, black fills, gray segments, gray fills; words and spans with font, size and
   direction (`get_text("dict")` line `dir` gives rotation).
2. **viewport (A2):** find the title words "ELECTRICAL PLAN - PLAN N" (bold, large). The viewport is the drawing
   area directly above that title, inside the same sheet cell. Recommended: find the long gray/black frame lines
   that divide the sheet into cells, pick the cell containing the title, viewport = cell area above the title
   band. Fallback: cluster black primitives above the title. Also parse `SCALE:` under the title.
   Test: page 1 viewport must contain the point (1150, 450) and must not contain (500, 450) (mechanical plan).
3. **legend (A2):** find the "LEGEND" title that is not part of "FLOOR FINISH LEGEND". Legend rows: symbol drawing
   on the left, description text on the right, small code text above or next to the symbol. Produce
   `LegendEntry` list with symbol geometry (for templates) and text. Rule-based mapping from description keywords to
   category/subtype; then Agente 4's `interpret_legend` refines it with Claude (optional, cached).
4. **symbols (A2):** inside the viewport, take black segments and black fills; remove wall outlines (long
   axis-aligned segments, segments touching gray wall fills), remove dashed wiring candidates (short open polylines
   forming chains, see wires) and keynote tags (text in small boxes). Cluster remaining primitives by proximity
   (bbox gap < about 1 pt, not only shared endpoints, because "$" is an S crossing a bar). Large symbols (ceiling fan
   = 4 blades + center circle) must be merged into one cluster.
5. **classify (A2):** compare each cluster with each legend template. Recommended: rasterize both at the same scale
   (no rescaling, symbols are drawn at the same size) on a small canvas centered on the bbox, test rotations
   0/90/180/270, score with IoU of dilated masks or chamfer distance. Add shape features (closed circle radius,
   fill ratio, segment count). Then attach code tokens: text words within about 14 pt of the cluster (handle rotated
   text). Codes refine subtype per section 2. Output a `Detection` with confidence; if best score is low or the
   top two are close, set `needs_review=True`.
6. **llm adjudication (A4):** for `needs_review` candidates, render crops and ask Claude to pick a label from the
   allowed list (or `not_a_component`). Claude never returns coordinates.
7. **rooms (A3):** build room polygons and assign `room_id` to every detection.
8. **bom (A8):** wires, boxes (optional flag).
9. Return `SheetResult` with timings, warnings and llm usage.

Performance target: under 60 s per sheet with cache warm; deterministic given the same inputs and cache.

---

## 6. Rooms algorithm (Agente 3)

1. Room labels: bold spans about 9.5 to 9.6 pt inside the viewport, joined per line, filtered with a lexicon
   (LIVING, KITCHEN, DINING, BED, BEDROOM, STUDIO, BATH, LNDRY, LAUNDRY, CL, CLOSET, WALK-IN, HALL, HALLWAY, OFFICE,
   PORCH, GARAGE, ENTRY, PANTRY) plus "IN ATTIC" (regular font) for the attic box.
2. Wall mask: rasterize gray wall fills plus black long segments (walls) at about 3 px per pt.
3. Close door openings: use door symbols (gray swing arcs and door leaves) to draw a closing line across each
   opening, and/or morphological closing with a kernel about the size of a wall gap. Windows are inside walls.
4. Flood fill from each label point. If one region contains several labels (open plan), split it by nearest label
   (geodesic or Euclidean Voronoi inside the region). Fill holes (furniture) so they belong to the room.
5. Building footprint = union of interior regions + walls. Outside footprint = "Exterior". The attic box polygon
   (gray rectangle around "IN ATTIC") is room "Attic" and has priority over the room below it.
6. Convert regions to polygons in PDF points (cv2.findContours + simplify).
7. `assign_room(detection, rooms)`: point in polygon on the symbol center; if the center lies on a wall (wall
   devices), use the nearest room within about 12 pt, preferring the side where the symbol body is. Flag
   `needs_review` when two rooms are within 4 pt.
8. Expose `assign_room(point, rooms) -> room_id` for the backend (used when a user moves a detection with
   `room_source == "auto"`).

---

## 7. AI with Claude (Agente 4)

Package `engine/takeoff_engine/llm/`:

- `client.py`: Anthropic SDK wrapper. Model from env. Structured output via tool use with a JSON schema generated
  from Pydantic; validate the response with Pydantic; on validation failure retry once with the error message.
  Retries only on 429, 5xx, timeouts and network errors, exponential backoff with jitter, max 3 attempts.
  Logs tokens and cost per call.
- `cache.py`: content-addressed cache keyed by sha256(model + prompt_version + inputs, including image bytes).
  Disk cache under `.cache/llm/` for the CLI; the backend may plug Redis. The demo must work from cache.
- `prompts/` (versioned files, e.g. `legend_v1.md`, `adjudicate_v1.md`); `prompt_version` is stored in results.
- Tasks:
  - `interpret_legend(entries, legend_png) -> list[LegendEntry]`: map each legend row to category/subtype and code
    meanings; read the notes for letter meanings. Unknown is allowed. Deterministic validation: enums must be valid.
  - `adjudicate(candidates, legend) -> list[Adjudication]`: batch of crops (rendered at about 300 dpi with the
    candidate outlined) plus legend thumbnails; answer a label from the allowed list or `not_a_component`, with a
    short reason and confidence. Never coordinates.
  - Optional, high value for the presentation: `baseline_vision_takeoff(sheet_png) -> counts` (LLM only), used by
    eval to compare "LLM alone" vs our hybrid.
- No API key: the engine still runs (rules only) and records a warning. Tests use recorded fixtures, never the network.

---

## 8. Bill of materials (Agente 8)

- **Wires:** dashed wiring = chains of short black open segments (dash about 4 to 10 pt, gap about 2 to 4 pt; measure
  and document real values). Chain by endpoint proximity and direction continuity. Snap both ends to the nearest
  device (within about 10 pt). One `WireRun` per device-to-device link. Length = polyline length / scale_pt_per_ft.
  Cable type: `nm_14_3` if both ends are 3-way switches (`three_way` or `three_way_dimmer`), else `nm_14_2`.
- **Routing assumption** (`data/assumptions.yaml`, shown in UI and docs): ceiling height 8 ft, switch box at 48 in
  AFF, so each switch end adds 4 ft vertical + 1 ft slack; each ceiling end adds 1 ft slack; plus 10% waste.
- **Boxes:** switches whose centers are within about 10 pt of each other along the same wall form one box with
  gangs = number of switches and one plate of the same gang size. Receptacles: 1-gang box + plate
  (weatherproof cover for WP). Ceiling fan: fan-rated ceiling box. Pendant, wall, exterior lights, smoke detectors and
  junction boxes: 4 in round/octagon ceiling box. Recessed lights and exhaust fans: integrated housing, no box
  (stated assumption). Draw each box with its gang label ("2G").
- **Pricing:** `data/price_list.yaml` with item_key, description, unit, unit_price, source (store + URL), captured_at.
  Prices must be real and sourced. If a price cannot be verified, mark `verified: false` and ask Santiago.
- **CRUD:** pure functions `compute_boxes(detections)`, `compute_bom(detections, wire_runs, boxes, prices, assumptions)`
  so the backend recomputes after every change (move a switch between locations, edit a run, change cable type).

---

## 9. Backend API (Agente 5)

- Upload: `POST /api/documents` (multipart PDF) stores the file, creates one sheet per page, enqueues one ARQ job per
  sheet, returns 202 `{document_id, sheets: [{sheet_id, page_index, job_id}]}`.
- `GET /api/jobs/{job_id}`: queued, running, succeeded, failed, with progress and error.
- `GET /api/documents/{id}`, `GET /api/sheets/{id}` (sheet + current run: rooms, detections, wire_runs, boxes, legend).
- `GET /api/sheets/{id}/image.png` (viewport rendered at `dpi`, cached on disk).
- Detections: `POST /api/sheets/{id}/detections`, `PATCH /api/detections/{id}`, `DELETE /api/detections/{id}`
  (soft delete). Responses include the updated takeoff. Moving a detection with `room_source == "auto"`
  re-assigns the room with `rooms.assign_room`.
- `GET /api/sheets/{id}/takeoff`, `GET /api/sheets/{id}/bom`, wire run and box CRUD endpoints,
  `GET /api/sheets/{id}/corrections`, `POST /api/sheets/{id}/reanalyze`, `GET /api/sheets/{id}/export.csv`,
  `GET /api/health`.
- Tables: documents, sheets, analysis_runs (pipeline_version, schema_version, model, prompt_versions, status,
  timings, llm_usage), rooms, legend_entries, detections, wire_runs, boxes, corrections (append-only event log with
  entity, action, before, after, created_at).
- Versioning: re-analysis creates a new run; previous runs and their corrections are never mutated. A sheet points
  to its current run. Idempotency: same file hash + pipeline version reuses the succeeded run.
- Feature flags (env): `ENABLE_LLM`, `ENABLE_BOM`.
- Until the engine is ready, a `FakeEngine` returns the fixture so the frontend can integrate.

---

## 10. Frontend (Agente 6)

- Home: upload PDF (or "Load demo plans"), list 4 sheets with job status (polling every 2 s).
- Sheet view: plan image with an SVG overlay whose `viewBox` is the viewport in PDF points (no coordinate math
  errors). Pan and zoom. Layer toggles: rooms (polygons + names), detections by category (color + icon), wires
  (label "14/2 - 12.4 ft"), boxes (label "2G"), needs-review highlight.
- Right panel tabs: Takeoff table (rooms x types + totals; clicking a cell or a total highlights exactly those marks
  on the plan), Details (read: type, subtype, codes, room, confidence, source, evidence), BOM (boxes, cable, priced
  total, assumptions), Corrections log.
- CRUD: select by click, drag to move, add mode (pick type, click on plan), change type/subtype/room from the details
  panel, delete with button or Delete key, undo last action. Optimistic updates with rollback on error. Counts come
  from the detection list in cache, so they update instantly.
- Clean, professional look (it will be screen-shared). Color legend always visible.
- Shared color palette (frontend AND `overlay.py` must use the same): ceiling_fan `#7C3AED`, light `#F59E0B`,
  switch `#2563EB`, receptacle `#059669`, exhaust_fan `#0891B2`, detector `#DC2626`, junction_box `#6B7280`,
  wires `#DB2777`, boxes `#111827`, rooms translucent fills with dark labels, needs_review dashed orange `#EA580C`.

---

## 11. Evaluation (Agente 7)

- Ground truth counted by hand by Santiago: `eval/ground_truth/plan{N}.counts.yaml` (room -> "category.subtype" ->
  count). Agente 7 creates the templates with room names and zeroed types, plus instructions.
- Optional detection-level truth: `eval/ground_truth/plan{N}.detections.json` exported from a human-reviewed sheet.
- `takeoff eval`: per type count error, per room exact-match rate, precision/recall by type when detection truth
  exists (match same type within 10 pt), markdown + JSON report in `eval/reports/`, overlay PNGs with true positives
  green, false positives red, false negatives orange.
- CI gate: tests + eval regression check against a committed baseline.

---

## 12. Release and support hooks (needed for the design doc)

- Every result stores pipeline_version, schema_version, model and prompt versions.
- Corrections are an append-only log: they are the labeled data to measure production accuracy and to improve rules,
  prompts or a future trained detector.
- Feature flags gate LLM and BOM. Re-analysis never overwrites a corrected takeoff.

## 13. Out of scope (state it honestly)

Authentication and multi-tenant (single demo user), cloud deployment (local Docker demo), raster/scanned plans
(the path would be template matching on raster + a trained detector fed by corrections).
