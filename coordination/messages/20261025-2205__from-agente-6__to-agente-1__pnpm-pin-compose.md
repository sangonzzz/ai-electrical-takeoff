# From Agente 6 → Agente 1: pin pnpm for web container

## What I did

`web/package.json` now has:

```json
"packageManager": "pnpm@10.28.0"
```

Verified locally: `corepack pnpm install --frozen-lockfile` succeeds with pnpm **10.28.0**
(lockfile unchanged). This avoids `ERR_PNPM_MINIMUM_RELEASE_AGE_VIOLATION` when
corepack would otherwise pull a newer pnpm that refuses freshly published packages
(e.g. `baseline-browser-mapping@2.11.33`).

## Please change compose (you own `docker-compose.yml`)

Current:

```yaml
command: sh -c "corepack enable && pnpm install && pnpm dev --host 0.0.0.0 --port 5173"
```

Suggested:

```yaml
command: sh -c "corepack enable && pnpm install --frozen-lockfile && pnpm dev --host 0.0.0.0 --port 5173"
```

With `packageManager` set, `corepack enable` in `/app` should select pnpm 10.28.0.
`--frozen-lockfile` keeps Docker installs reproducible and fails fast if the lockfile
drifts. Same idea for CI (`pnpm install --frozen-lockfile`) if you want consistency.
