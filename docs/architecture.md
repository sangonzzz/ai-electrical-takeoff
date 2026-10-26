# Architecture

Technical overview for **AI Electrical Takeoff**. Contracts:
`engine/takeoff_engine/models.py`. Counting: only `compute_takeoff` (frontend mirror:
`web/src/lib/takeoff.ts`). Spec: [`SPEC.md`](SPEC.md). Decisions:
[`../coordination/DECISIONS.md`](../coordination/DECISIONS.md).

---

## Component diagram

```mermaid
flowchart TB
  subgraph clients [Clients]
    WEB[React web<br/>Vite · TanStack Query · Zustand]
    CLI[takeoff CLI]
  end

  subgraph compose [Docker Compose]
    API[FastAPI api :8000<br/>image takeoff-backend]
    WRK[ARQ worker<br/>same image]
    DB[(Postgres 16)]
    REDIS[(Redis 7)]
    WEBCTR[web :5173<br/>Node / pnpm]
  end

  subgraph engine [takeoff_engine]
    PC[pdf_context]
    VP[viewport + scale]
    LG[legend + templates]
    SY[symbols + classify]
    LLM[llm Claude<br/>legend / adjudicate]
    RM[rooms]
    BOM[wires · boxes · bom]
    TO[compute_takeoff]
    OV[overlay]
  end

  PDF[(PDF plans)]
  STORE[(storage/ · .cache/)]

  WEB --> WEBCTR
  WEBCTR --> API
  CLI --> engine
  API --> REDIS
  WRK --> REDIS
  API --> DB
  WRK --> DB
  WRK --> engine
  API --> TO
  API --> STORE
  WRK --> STORE
  PDF --> PC
  PC --> VP --> LG --> SY
  SY --> LLM
  SY --> RM --> BOM
  BOM --> OV
  LLM -.->|labels only<br/>never coordinates| SY
```

### Why hybrid (not “send the whole plan to a vision model”)

Plans are **fully vector**. Geometry gives exact positions; vision LLMs miscount dense
symbols, drift in coordinates, and cost more. Claude is used only for **WHAT**
(legend rows, ambiguous candidates). Coordinates always come from PyMuPDF primitives.

---

## Data flow: upload → job → engine → DB → UI → corrections

```mermaid
sequenceDiagram
  participant U as User / UI
  participant API as FastAPI
  participant Q as Redis / ARQ
  participant W as Worker
  participant E as Engine
  participant DB as Postgres

  U->>API: POST /api/documents (PDF multipart)
  API->>DB: document + sheets + analysis_runs<br/>pipeline_version = PIPELINE_VERSION
  API->>Q: enqueue one job per page
  API-->>U: 202 { document_id, sheets[{sheet_id, page_index, job_id}] }

  loop each sheet
    Q->>W: analyze_sheet_job
    W->>E: analyze_sheet(pdf, page_index)
    Note over E: pdf_context → viewport → legend<br/>→ symbols → classify → rooms → BOM
    E-->>W: SheetResult
    W->>DB: rooms, detections, legend,<br/>wire_runs, boxes, run=succeeded
  end

  U->>API: GET /api/sheets/{id} + image.png
  API-->>U: sheet + current run + overlay data

  U->>API: PATCH / POST / DELETE detection<br/>(or move with room_source=auto)
  API->>E: compute_takeoff (+ compute_bom / boxes)
  API->>DB: update entities + append corrections log
  API-->>U: updated takeoff + BOM
```

### Idempotency and versioning

Re-upload of the same file hash reuses a **succeeded** run for
`(file_hash, page_index, pipeline_version)` when `pipeline_version` matches
`PIPELINE_VERSION` in `engine/takeoff_engine/__init__.py`. Engine behavior changes
bump that semver (after Santiago’s approval from v0.4.0) so clients never get stale
marks for a new pipeline.

Re-analyze creates a **new** run; previous runs and corrections are not mutated.

---

## Engine pipeline (per sheet)

| Step | Module | Owner | Role |
|------|--------|-------|------|
| 1 | `pdf_context` | A1 | Styled segments/fills, words/spans |
| 2 | `viewport` | A2 | Electrical cell + scale |
| 3 | `legend` | A2 | Rows + templates; optional LLM interpret |
| 4 | `symbols` / `classify` | A2 | Candidates → detections + codes |
| 5 | `llm.adjudicate` | A4 | Optional labels for `needs_review` |
| 6 | `rooms` | A3 | Polygons + room assignment |
| 7 | `wires` / `boxes` / `bom` | A8 | Optional BOM |
| 8 | `overlay` | A7 | Debug / eval PNGs |
| — | `compute_takeoff` | A1 | Pure counts |

CLI: `takeoff analyze --page N` with **N = plan number 1..4** → `page_index = N - 1`.

---

## Backend and frontend

- **API:** FastAPI, SQLAlchemy 2 async, Alembic, ARQ. Image cache under `.cache/`;
  PDFs under `storage/`. Feature flags: `ENABLE_LLM`, `ENABLE_BOM`, `ENGINE=real|fake`.
- **UI:** React + Vite; SVG overlay `viewBox` = electrical viewport in PDF points
  (no coordinate remapping bugs). Takeoff table click highlights matching marks.
  Optimistic CRUD with rollback; shared color palette with `overlay.py` (SPEC §10).

---

## Principles

1. Geometry = **where**; legend + Claude = **what**. Claude never returns coordinates.
2. `compute_takeoff` is the only counting path.
3. Contracts are frozen; Agente 1 owns schema/TS regeneration.
4. Corrections are append-only; re-analysis never silently overwrites a corrected run’s history.
5. Engine freeze from **v0.4.0**: behavior changes only with Santiago’s approval (`AGENTS.md` §14).
