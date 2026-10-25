# Architecture

High-level data flow (Agente 1). Details live in `docs/SPEC.md`.

```mermaid
flowchart LR
  PDF[PDF plans] --> PC[pdf_context]
  PC --> VP[viewport]
  PC --> LG[legend]
  VP --> SY[symbols]
  LG --> CL[classify]
  SY --> CL
  CL --> LLM[llm adjudicate]
  CL --> RM[rooms]
  LLM --> RM
  RM --> BOM[wires / boxes / bom]
  RM --> SR[SheetResult]
  BOM --> SR
  SR --> API[FastAPI + ARQ]
  API --> WEB[React overlay + CRUD]
  SR --> TO[compute_takeoff]
```

## Principles

1. Geometry decides **where**; legend + Claude decide **what**. Claude never returns coordinates.
2. `compute_takeoff` is the only counting path (engine + mirrored in the frontend).
3. Contracts in `engine/takeoff_engine/models.py` are frozen; changes go through Agente 1.
