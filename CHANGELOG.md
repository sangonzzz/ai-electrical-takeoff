# Changelog

Plain-language notes for Santiago. Newest first.

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
