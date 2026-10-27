# Decisions (counting rules and assumptions)

Owned by Agente 1. Others request changes via `coordination/messages/`.
Copied from `docs/SPEC.md` section 2 so agents have a short reference.

## Counting rules

1. Kitchen and Dining are separate rooms only when the plan labels them separately
   (Plan 2: yes; Plans 1 and 3: one room "Kitchen / Dining").
2. A component outside the building footprint counts under the room "Exterior"
   (porch light, WP receptacle, outdoor heat pump receptacle).
3. A combined fixture counts once under its combined type (fan/light, smoke/CO).
4. Switch type follows the letter next to the switch symbol, as defined by that
   sheet's legend and notes.
5. Assumption: the ceiling fan symbol includes a `J` circle at its center. It
   counts as ONE ceiling fan, not as a ceiling fan plus a junction box. A
   standalone `J` circle is a junction box.
6. Assumption: devices inside the "IN ATTIC" box belong to a room "Attic"
   (kind `attic`).
7. Assumption: open-plan boundaries between labels are split by nearest label
   (see rooms algorithm). The boundary is drawn on the plan and the user can
   reassign any detection.
8. Repeated labels get a suffix in display name: "CL 1", "CL 2" (ordered left
   to right, top to bottom).
9. Only the electrical plan viewport is analyzed; mechanical and finish plans
   are excluded.

## Count keys

Detections use `category` + `subtype`. Count keys are `category` and
`category.subtype` (see taxonomy in SPEC section 2 / `models.SUBTYPES`).

## Receptacle subtype priority

When several codes apply: `240V` > `MW` / `DW` / `H` / `FC` > `WP` > half-hot >
`GFI` > `AFI` > plain duplex.

## Rooms (Agente 3)

1. Open-plan split uses **Euclidean nearest label** (Voronoi) inside a shared
   flood-fill region — not geodesic distance.
2. Plan 3 has **4** `CL` labels in the electrical viewport; Plan 4 has **2**
   (SPEC §1 updated to match). Keep all and number `CL 1`….
3. Exterior room has an empty polygon; assignment = outside building footprint.
4. Viewport comes from `find_electrical_viewport` (Agente 2), not `APPROX_VIEWPORTS`.

## LLM (Agente 4)

1. Vision tasks (`interpret_legend`, `adjudicate`, `baseline_vision_takeoff`) use
   Sonnet (`ANTHROPIC_MODEL`, default `claude-sonnet-5-5`). Haiku is reserved for
   future high-volume text-only work.
2. Optional kwargs on the three public LLM functions: `usage`, `warnings`, `client`
   — required scaffold signatures unchanged.
3. No API key: warn + rules-only / empty adjudication / empty baseline; never raise.
4. Adjudicate batches ~6 candidates; crop ~300 dpi, 18 pt pad, red outline.
   Labels = `category.subtype` or `not_a_component`.
5. **Sonnet 5.5 does not support forced tool use** (`tool` / `any` → HTTP 400).
   Client uses `tool_choice: auto` + `strict: true` tools + prompt requiring one
   `submit_result` call; maps as list-of-pairs for `additionalProperties: false`.

## BOM (Agente 8)

1. Routing: plan polyline length + vertical allowance from assumptions; **10% waste
   applied in `compute_bom`**, not in `WireRun.total_length_ft`.
2. Measured Plan 1 dash median **7.1 pt**, gap median **3.8 pt**; code windows
   dash 3–12 pt, gap 1–6 pt.
3. Cable: `nm_14_3` only when both ends are `three_way` or `three_way_dimmer`;
   else `nm_14_2`.
4. Boxes: recessed lights and exhaust fans → `kind: none`. Wall / pendant /
   exterior lights → `ceiling_round`.
5. Prices: Home Depot when verified; unverified SKUs left for Santiago (see A8 status).

## Symbols / pipeline (Agente 2)

1. Wiring filter keeps elongated dash chains; compact blobs (fans/lights) stay.
2. Ceiling fan prior: size ≥70 pt, aspect <1.35, ≥40 segments, plus template match.
3. Degenerate legend templates (side <2.5 pt) ignored; NMS 8 pt per category.

## Frontend (Agente 6)

1. Fixture sheets 2–4 reuse Plan 1 sample geometry with renamed ids (4 cards before
   real analysis).
2. Fixture BOM is a lightweight derivation of sample wires/boxes until API serves BOM.
3. Drag commits PATCH only on mouseup; frames update React Query cache locally.

## Backend (Agente 5)

1. Job id = `analysis_runs.id` (no separate jobs table).
2. `INLINE_JOBS=true` in tests; `ENGINE=fake` until real pipeline is default.
3. Entity ids uniquified per run (`id__{runTag}`) for FakeEngine reanalyze.

## Eval (Agente 7)

1. Room names in GT templates use display_name style (`Laundry`, `CL 1`, Attic/Exterior).
2. Detection match: greedy nearest neighbour, same `category.subtype`, ≤10 pt.
3. Without pipeline results, Plan 1 eval smoke uses contracts fixture.

## Scaffold / integration (Agente 1)

- Git author: `sangonzzz` / `santiagonzalezmora@gmail.com`.
- Unassigned detections still increment sheet `totals`.
- `sqlalchemy[asyncio]` + `greenlet` required for async SQLAlchemy (backend).
- CI workflow file may need `gh` token `workflow` scope to push to GitHub.
- **CLI `--page` is 1-based** (Plan 1..4). Convert with `page_index = page - 1` before
  calling `analyze_sheet` / `load_page`. Contracts and engine APIs stay 0-based
  `page_index`. Do not squash or rewrite git history; Cursor co-author trailers OK.
- **Single `PIPELINE_VERSION`** in `engine/takeoff_engine/__init__.py` only; bump on any
  engine behavior change. `ENGINE=real` is the compose/.env default (`fake` for tests).
- **Engine freeze:** current frozen tag **v0.6.3**. No engine behavior changes without
  Santiago’s approval (AGENTS.md §14).
