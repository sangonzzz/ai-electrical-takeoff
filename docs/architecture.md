# Architecture

Technical overview for AI Electrical Takeoff. Contracts live in
`engine/takeoff_engine/models.py`; counting is only `compute_takeoff`.

## Component diagram

```mermaid
flowchart TB
  subgraph clients [Clients]
    WEB[React web<br/>Vite + TanStack Query]
    CLI[takeoff CLI]
  end

  subgraph compose [Docker Compose]
    API[FastAPI api :8000]
    WRK[ARQ worker]
    DB[(Postgres 16)]
    REDIS[(Redis 7)]
  end

  subgraph engine [takeoff_engine]
    PC[pdf_context]
    VP[viewport + legend]
    SY[symbols + classify]
    RM[rooms]
    LLM[llm Claude]
    BOM[wires / boxes / bom]
    TO[compute_takeoff]
    OV[overlay]
  end

  PDF[(escondido_plans.pdf)]
  WEB --> API
  CLI --> engine
  API --> REDIS
  WRK --> REDIS
  API --> DB
  WRK --> DB
  WRK --> engine
  API --> TO
  PDF --> PC
  PC --> VP --> SY --> LLM
  SY --> RM --> BOM
  BOM --> OV
```

## Data flow: upload → corrections

```mermaid
sequenceDiagram
  participant U as User / UI
  participant API as FastAPI
  participant Q as Redis / ARQ
  participant W as Worker
  participant E as Engine
  participant DB as Postgres

  U->>API: POST /api/documents (PDF)
  API->>DB: document + 4 sheets + analysis_runs
  API->>Q: enqueue 4 jobs
  API-->>U: 202 document_id + job ids
  loop each sheet
    Q->>W: job
    W->>E: analyze_sheet / FakeEngine
    E-->>W: SheetResult
    W->>DB: rooms, detections, wires, boxes, run=succeeded
  end
  U->>API: GET sheet + image.png
  API-->>U: overlay data
  U->>API: PATCH detection / CRUD
  API->>E: compute_takeoff (+ BOM)
  API->>DB: corrections log + updated entities
  API-->>U: takeoff + BOM
```

## Principles

1. Geometry decides **where**; legend + Claude decide **what**. Claude never returns coordinates.
2. `compute_takeoff` is the only counting path (mirrored in `web/src/lib/takeoff.ts`).
3. Contracts are frozen; Agente 1 regenerates `contracts/schema.json` and `web/src/types/contracts.ts`.
4. Re-analysis creates a new run; corrections are append-only.
5. Feature flags: `ENABLE_LLM`, `ENABLE_BOM`, `ENGINE=fake|real`.
