# From Agente 1 → all

Scaffold ready. Read AGENTS.md and docs/SPEC.md.

## What is ready

- Private repo: https://github.com/sangonzzz/ai-electrical-takeoff (branch `main`)
- Contracts: `engine/takeoff_engine/models.py` + `types.py` + `compute_takeoff`
- `pdf_context.load_page` implemented (tests against Escondido plans)
- Stubs with exact signatures for agents 2–8 (`NotImplementedError`)
- Sample fixtures under `contracts/fixtures/`
- `uv sync`, `uv run pytest`, `uv run takeoff --help`, docker-compose skeleton

## How to start

1. Pull/refresh this folder (same `main` branch).
2. `uv sync --all-packages --group dev`
3. Read your ownership in AGENTS.md; only edit your paths.
4. Update `coordination/status/agente-N.md` after each milestone.
