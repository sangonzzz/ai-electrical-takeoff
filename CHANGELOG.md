# Changelog

Plain-language notes for Santiago. Newest first.

## app v1.0.3 (UI only, PIPELINE_VERSION 0.6.7)

UI-only app patch (git tag **`v1.0.3`**). Analysis / golden unchanged.

- **BOM total card:** estimated material cost summary; `data-testid="bom-total"` is amount-only (`$…`).
- **Locale-proof number fields:** Plan length / Vertical / X / Y use a shared decimal input.
- **Simplified cable handles:** dense runs show fewer edit handles (RDP ≤12).

Engine freeze at **0.6.7** still applies for detection/rooms/LLM/BOM tracing.

## app v1.0.2 (UI only, PIPELINE_VERSION 0.6.7)

UI-only app patch (git tag **`v1.0.2`**). Analysis / golden unchanged.

- **Assumptions card:** collapsible BOM assumptions (hidden by default).
- **Human labels:** assumption keys shown in plain language; dash/gap keys hidden.
- **Prominent total:** BOM total at the top as `Total $…` (e2e-compatible).
- **Vitest:** BomPanel / assumptions helpers cover total selector + formatting.

Engine freeze at **0.6.7** still applies for detection/rooms/LLM/BOM tracing.

## App v1.0.1 — cable colors + edit handles

UI-only app patch (git tag **`v1.0.1`**). **`PIPELINE_VERSION` stays `0.6.7`**
(analysis / golden unchanged).

- **Cable colors by type:** wire runs colored by cable type (e.g. 14/2 vs 14/3)
  instead of a single pink stroke.
- **Edit handles:** visible handles when editing cables for clearer tip / geometry
  interaction.

Engine freeze at **0.6.7** still applies for detection/rooms/LLM/BOM tracing.

## v1.0.0 — interview release (`PIPELINE_VERSION` 0.6.7)

Final freeze of **engine and app** for the interview demo. Git tag **`v1.0.0`**;
engine semver **`0.6.7`**. Further app UI patches (e.g. v1.0.1) may ship without
bumping the pipeline; engine behavior still needs Santiago’s approval (`AGENTS.md` §14).

Golden lock: `eval/golden/current/` (see `eval/golden/CHANGES.md` vs v0.6.4).

### Known limits

- **Plan 3 half-hot:** one `receptacle.afci_half_hot` (~895.8, 505.7) is not
  detected vs earlier goldens (detections 71→70; cascading boxes/wires).
- **Plan 4 water heater receptacle:** review-flag / WH receptacle behavior on
  plan 4 remains imperfect (accepted `needs_review` drift on nearby GFCI /
  240V devices; see golden CHANGES).
- **Millwork traced as cable:** some cabinet/millwork dashed ink still becomes
  pink wire runs (Wires layer is beta; prefer Edit cables / manual delete).

## v0.6.7 — interview engine lock

Pipeline bump paired with **v1.0.0**. Documents known limits above; analysis
fingerprint locked in `eval/golden/current/`.

## v0.6.6 — Mech. Closet B14 + longest-boundary merge (frozen)

Rooms closet / merge rules (final):

- **Closet:** deep footprint hole + keynote within ~14 pt → `Mech. Closet (<tag>)`
  any size (even if the closet touches an exterior wall; tags sit on wall poche).
- **240V without keynote:** deep hole + `240V` text → `Mech. Closet (B14)` when B14
  is off-viewport (plans 2/3); pick candidate nearest Laundry.
- **Merge:** other deep holes merge into the labeled neighbor with the longest
  shared boundary (dilate ~1 wall width; nearer label ≤75 pt wins when competing).
  Never emit `Unlabeled space`.
- **Shallow niches:** leave unclaimed → Exterior (e.g. B38 outdoor unit).

Engine was frozen after this tag until the v1.0.0 / 0.6.7 interview release.

## v0.6.5 — pocket rule + prices + cable-edit response (frozen)

Engine patch + related app fixes:

- **Unlabeled pocket rule (tightened):** deep footprint hole (≥8 pt inside outline),
  area ≥ **9 sq ft** @ 18 pt/ft; keynote → `Mech. Closet (TAG)` only if tag bbox is
  fully inside the pocket; smaller deep holes merge into nearest labeled room
  (not Exterior). Removes Plan 1 false `Unlabeled space 1` / `Mech. Closet (B32)`.
- **Prices:** Home Depot–verified SKUs in `data/price_list.yaml`; BOM by subtype;
  Fixtures (allowance) section.
- **Cable-edit response fix:** PATCH move / wire CRUD return fresh boxes + BOM
  (same as a subsequent GET; no stale identity-map collections).

Engine was frozen after this tag until Santiago approved the v0.6.6 closet/merge rules.

## App 0.7.0: editable cables and boxes

Application release (git tag **`v0.7.0`**). At ship time **`PIPELINE_VERSION` was `0.6.4`**
(analysis / golden unchanged).

- **Edit cables** in the UI (toggle): select runs, change 14/2↔14/3, create A→B,
  soft-delete / restore, drag devices → reattach tips; boxes stay derived (1G/2G/3G).
- **Backend** wire-run CRUD + `bom_edit` recompute without re-tracing the plan;
  undo/redo covers cable corrections; Excel/PDF exports reflect edits.
- **Golden** lock at `eval/golden/v0.6.4/` + isolated e2e (`takeoff_e2e` / `:5174`)
  for demo-flow and cable-edit.

Engine freeze at **v0.6.4** applied until the v0.6.5 pocket-rule bump.

## v0.6.4 — B14 closet / unlabeled interior rooms (frozen)

Rooms: unlabeled enclosed pockets inside the building footprint are interior rooms,
not Exterior.

- **B14 closet rule:** keynote (e.g. `B14`) in/near the pocket → `Mech. Closet (B14)`.
- Else → `Unlabeled space N` (reading order). Exterior = outside footprint only.

Engine was frozen after this tag until Santiago approved the v0.6.5 pocket tighten.

## v0.6.3 — wires restore + patches (frozen)

Approved wires restore to v0.6.0 geometry (`6ffe668`) plus two small patches:

- **Wires restored** to v0.6.0 best geometry (undo v3.1 wall/door tracing regression).
- **B38 exclusion:** keynote + outdoor equipment (`gfci_240v` / `B38`) ink never used as endpoints.
- **3-way rule:** either-end `three_way` / `three_way_dimmer` → cable type `nm_14_3`.

Engine was frozen after this tag until Santiago approved the v0.6.4 rooms fix.

## v0.6.2 — engine patch (frozen)

Patch bump for approved post-0.6.1 engine fixes. Engine was frozen after this tag
until Santiago approved the v0.6.3 wires restore.

## v0.6.1 — engine patch

Patch bump so idempotency picks up approved post-0.6.0 engine fixes.

## v0.6.0 — final engine (frozen)

Final engine release for the demo / interview build. Detection, rooms, LLM rules,
wires/BOM, and overlay behavior are **frozen** from this tag: no further engine
changes without Santiago’s explicit approval (`AGENTS.md` §14).

Backend, frontend, eval docs, and non-behavior test lock-ins may continue.

## v0.5.1 — engine patch

Patch bump so backend idempotency picks up the latest engine behavior after
post-0.5.0 fixes (same minor line as round 6 / LLM rules / wires v2).

## v0.5.0 — round 6 engine + LLM rules + wires v2

Approved engine bump after further precision work:

- **Round 6 engine:** additional detection / classify polish.
- **LLM rules:** tighter legend / adjudication rules for ambiguous symbols.
- **Wires v2:** improved dashed-run chaining and 3-way cable typing.

Also: backend deps `openpyxl` + `reportlab` for Excel / PDF quote exports (Agente 5).

## v0.4.0 — engine freeze (precision rounds 3–5)

Detection / BOM precision after v0.3.x:

- **Precision rounds 3–5:** further false-positive cuts and classify/rooms polish.
- **Geometric recessed rule:** recessed lights keyed more on geometry, not only legend IoU.
- **3-way cables:** `nm_14_3` wiring between three-way switch ends hardened.
- **Per-plan regression guard:** eval / regression checks that catch plan-level count regressions.

**Engine freeze:** from this tag, engine behavior changes only with Santiago’s approval
(see `AGENTS.md` §14). Bumps still go through Agente 1 when approved.

## v0.3.1 — Docker web fix + engine patch after A2/A8

- **Compose web:** `VITE_API_BASE_URL=http://localhost:8000` (was wrong `VITE_API_URL`).
  Anonymous volumes for `/app/node_modules` and `/app/.pnpm-store` so pnpm installs
  Linux binaries inside the container (Windows host `node_modules` no longer shared).
- **Pipeline version** bumped to `0.3.1` after Agente 2 / Agente 8 engine behavior
  changes so idempotency does not reuse `0.3.0` runs.

## v0.3.0 — review workflow, idempotency, single pipeline version

- **One version string:** `PIPELINE_VERSION` / `__version__` = `0.3.0` only in
  `engine/takeoff_engine/__init__.py`. CLI (`takeoff --version` and analyze output),
  `SheetResult.pipeline_version`, and backend idempotency all share it.
- **Rule:** any engine behavior change bumps at least the patch (see `AGENTS.md` §13)
  so re-upload never reuses a stale analysis run for the same PDF hash.
- **Defaults:** `ENGINE=real` in `docker-compose.yml` and `.env.example` (`fake` for tests only).
- **Review / API:** backend review workflow and fix so idempotency uses the engine
  package version (not a divergent scaffold / agent-local label).

## v0.2.0 — precision rounds

Detection and rooms precision work after the first integration tag: tighter symbol
clustering / classify, rooms assignment polish, BOM snap improvements, eval overlays,
and frontend/API wiring so marks and counts stay reviewable on the plan.

*(Historical note: some local pipeline labels used `0.2.0-a2` before the single
`PIPELINE_VERSION` source existed; that is retired in v0.3.0.)*

## v0.1.0 — first full integration

First tagged release of the parallel-agent scaffold plus integrated pieces.

- **What it is:** upload/analyze residential electrical plan PDFs, show marks on the
  plan, per-room takeoff counts, optional BOM, CRUD corrections.
- **Engine:** vector `pdf_context`, viewport/legend/symbols/classify pipeline,
  rooms, Claude legend/adjudication (optional), wires/boxes/BOM, overlays + eval.
- **App:** FastAPI + ARQ + Postgres + Redis; React UI (fixture mode and API mode).
- **CLI:** `takeoff analyze` / `eval` / `schema`. `--page` is the **plan number 1..4**
  (Plan 1 = first sheet); internal `page_index` stays 0-based.
- **Docs:** `docs/SPEC.md`, `docs/architecture.md`, `coordination/DECISIONS.md`,
  per-module docs under `docs/modules/`.
- **Known limits:** detection accuracy still improving; ground-truth count YAMLs
  need Santiago’s hand counts; Docker Desktop required for full stack E2E; some
  BOM prices unverified; GitHub Actions workflow needs `workflow` token scope to
  publish CI.
