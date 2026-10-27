# Changelog

Plain-language notes for Santiago. Newest first.

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
