# Changelog

Plain-language notes for Santiago. Newest first.

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
