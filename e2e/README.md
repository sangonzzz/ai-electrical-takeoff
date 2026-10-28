# E2E (Agente 7)

Playwright quality pass against an **isolated** docker stack. It must never use
Santiago’s review database.

## Why isolation

`POST /api/documents/demo` (“Load demo plans”) is **idempotent by file hash**.
The same Escondido PDF always returns the same document/sheets. If Playwright
runs against the default stack (`localhost:5173` → API `:8000` → Postgres DB
`takeoff`), every add / delete / X-Y edit lands in the document Santiago reviews.

## Isolated stack

| Piece | Default (Santiago) | E2E |
|-------|--------------------|-----|
| Web | `:5173` | `:5174` |
| API | `:8000` | `:8001` |
| Postgres | `:5432` / DB **`takeoff`** | `:5433` / DB **`takeoff_e2e`** |
| Redis | `:6379` | `:6380` |
| Compose project | (root `docker-compose.yml`) | `takeoff-e2e` (`e2e/docker-compose.yml`) |
| Storage volume | `storage/` | named volume `storage_e2e` |

Postgres is created with `POSTGRES_DB=takeoff_e2e`. The API entrypoint runs
`alembic upgrade head` from `/app/backend`. We set `AUTO_MIGRATE=false` because
the lifespan bootstrap currently resolves Alembic’s relative `script_location`
from cwd `/app` and crashes (tracked with Agente 5).

## Run

```bash
# From repo root — preferred
cd e2e
npm install
npm test                 # up stack + Playwright (E2E_BASE_URL=http://localhost:5174)

npm run stack:up         # start only
npm run stack:down       # stop containers (keep volumes)
npm run stack:reset      # stop + delete volumes (wipe takeoff_e2e)
```

Or explicitly:

```bash
docker compose -f e2e/docker-compose.yml -p takeoff-e2e up -d --build --wait
set E2E_BASE_URL=http://localhost:5174   # PowerShell: $env:E2E_BASE_URL=...
cd e2e && npx playwright test
```

`scripts/run.mjs` **refuses** `E2E_BASE_URL` pointing at `:5173` unless you set
`E2E_ALLOW_DEFAULT_STACK=1` (do not use that for normal runs).

## Makefile

Ask Agente 1 to point `make e2e` at `cd e2e && npm test` so it always uses this
stack. Until then, use `cd e2e && npm test` — do **not** run Playwright against
`:5173`.

## Suites

| Spec | What |
|------|------|
| `tests/demo-flow.spec.ts` | Demo load, marks, palette add, undo/redo, X/Y, Excel/PDF |
| `tests/cable-edit.spec.ts` | Edit cables: select/type/delete/create, reshape/reconnect handles, Delete key, move switch, undo |

Unfinished contract pieces use `test.skip(reason)` so overnight runs stay green.

## Results

- Step table: `e2e/results/steps.md`
- Downloads (Excel/PDF checks): `e2e/results/downloads/`
- Artifacts on failure: `e2e/results/artifacts/`

## Golden analysis lock

`engine/tests/eval/test_golden.py` compares `analyze_sheet(..., use_llm=False, with_bom=True)`
to `eval/golden/current/planN.json` (see `eval/golden/CHANGES.md` for accepted diffs vs v0.6.4).

## Requirements

- Docker with Compose v2 (`--wait` supported)
- Image build uses repo `backend/Dockerfile` (`takeoff-backend:local`)
- Optional repo-root `.env` (e.g. `ANTHROPIC_API_KEY`) is passed into api/worker
  so demo analysis can finish
