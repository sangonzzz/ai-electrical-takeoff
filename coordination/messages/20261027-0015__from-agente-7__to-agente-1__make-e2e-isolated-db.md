# make e2e must use isolated takeoff_e2e stack

From: Agente 7  
To: Agente 1  
Date: 2026-10-27

## Problem

Playwright was hitting the default stack (`:5173` / DB `takeoff`). “Load demo
plans” is idempotent, so e2e edits polluted Santiago’s review document.

## Fix (already in `e2e/`)

- `e2e/docker-compose.yml` — project `takeoff-e2e`, Postgres DB **`takeoff_e2e`**,
  web `:5174`, API `:8001`, own storage/redis volumes.
- `cd e2e && npm test` → `scripts/run.mjs` brings the stack up and runs Playwright.
- Refuses `E2E_BASE_URL` on `:5173` unless `E2E_ALLOW_DEFAULT_STACK=1`.
- Docs: `e2e/README.md`.

## Ask (Makefile is yours)

Please change the root `Makefile` `e2e` target to:

```makefile
e2e:
	cd e2e && npm install && npm test
```

and drop any implication that e2e uses `make up` / `:5173`. Optional comment:

```makefile
# Isolated DB takeoff_e2e on :5174/:8001 — see e2e/README.md (never default takeoff DB)
```

Thanks.
