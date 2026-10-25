# AI Electrical Takeoff

Analyze residential electrical plan PDFs (vector) and produce a reviewable takeoff
with per-room counts, plan overlays, CRUD corrections, and an optional bill of materials.

## Status

Scaffold by Agente 1. Agents 2–8 implement detection, rooms, LLM, backend, frontend,
eval, and BOM against the frozen contracts in `docs/SPEC.md`.

## Quick start

```bash
cp .env.example .env
# fill ANTHROPIC_API_KEY if you want LLM features
uv sync --all-packages --extra dev
uv run pytest
uv run takeoff --help
docker compose up -d   # api / worker / web once Agente 5–6 land
```

## Layout

See `docs/SPEC.md` section 3 and `AGENTS.md` for ownership.

## Demo plans

`data/plans/escondido_plans.pdf` — City of Escondido PAADU public-domain plans (4 sheets).
