# Agente 7 — Evaluation, overlay, CI checks

## Estado

E2E isolated on DB **`takeoff_e2e`** (compose project `takeoff-e2e`, web `:5174`,
API `:8001`). Documented in `e2e/README.md`. Default `takeoff` DB untouched.

## Hecho

- `e2e/docker-compose.yml` — own Postgres/Redis/storage; DB name `takeoff_e2e`.
- `e2e/scripts/run.mjs` — `npm test` brings stack up + Playwright; refuses `:5173`.
- Verified: demo doc IDs differ on `:8001` vs `:8000`; pg only has `takeoff_e2e`
  in the e2e Postgres.
- Messages: Agente 1 (`make e2e` → `npm test`), Agente 5 (alembic path bug).

## Cómo probarlo

```bash
cd e2e && npm test          # isolated stack + suite
npm run stack:up            # :5174 only
npm run stack:down
npm run stack:reset         # wipe takeoff_e2e volumes
```

Santiago keeps reviewing on **http://localhost:5173** (`make up`).

## Siguiente

- Agente 1: wire `make e2e` to `cd e2e && npm test`.
- Agente 5: fix absolute alembic `script_location` so `AUTO_MIGRATE` works in e2e.

## Bloqueos

Ninguno para isolation. `make e2e` still old until A1 updates Makefile.

## Decisions

- Full separate compose project (not a second DB on Santiago’s Postgres) so a
  mistake cannot hit `takeoff`.
- `AUTO_MIGRATE=false` + entrypoint migrate until A5 fixes path resolution.

## Needs from Santiago

None. Review UI on `:5173` is safe from e2e again.

## Explicación para Santiago

Las pruebas del navegador ya **no tocan** tu base `takeoff`. Levantan otro Docker
(`takeoff-e2e`) con su propia Postgres `takeoff_e2e`, web en el puerto **5174** y
API en **8001**. “Load demo plans” ahí crea otro documento; el tuyo en 5173 queda
limpio. Cómo correrlo: `cd e2e && npm test` (detalle en `e2e/README.md`).
