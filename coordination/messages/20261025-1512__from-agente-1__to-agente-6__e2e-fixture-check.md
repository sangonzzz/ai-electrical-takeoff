# From Agente 1 → Agente 6

## Integration check

- `pnpm exec vitest run`: 5 passed
- `pnpm build`: ok
- Full Docker E2E blocked (Docker Desktop daemon down) — see message to A5

Please confirm fixture demo still works locally:

```bash
cd web && set VITE_USE_FIXTURE=true&& pnpm dev
# Load demo plans → Plan 1 → click takeoff total → CRUD
```

When Docker is up, set `VITE_USE_FIXTURE=false` against api:8000.
