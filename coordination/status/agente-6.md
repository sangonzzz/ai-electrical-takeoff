# Agente 6 — Frontend (web/)

## Estado

pnpm pinned to 10.28.0 via `packageManager`; frozen-lockfile verified; compose change asked of A1.

## Hecho

- Demo polish (takeoff subtypes, filters, fit, review/export) — previous milestone
- Pin `"packageManager": "pnpm@10.28.0"` in `web/package.json` (fixes Docker
  `ERR_PNPM_MINIMUM_RELEASE_AGE_VIOLATION` when corepack grabs newest pnpm)
- Confirmed `corepack pnpm install --frozen-lockfile` works with 10.28.0
- Message to Agente 1: compose should use `pnpm install --frozen-lockfile`

## Cómo probarlo

```bash
cd web
corepack enable
corepack prepare pnpm@10.28.0 --activate   # or: corepack pnpm …
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
pnpm exec vitest run
pnpm dev
```

## Siguiente

- Wait for Agente 1 to update `docker-compose.yml` web command
- Optional: undo endpoint when A5 adds one

## Bloqueos

- Compose still runs unpinned `pnpm install` until Agente 1 lands the change

## Decisions

- Pin exactly the lockfile-era pnpm (10.28.0), not latest
- Recommend `--frozen-lockfile` in Docker/CI for reproducible installs

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

El contenedor web fallaba porque corepack bajaba un pnpm muy nuevo que rechaza
paquetes recién publicados (minimum release age). Fijé `packageManager` a
`pnpm@10.28.0` (la versión con la que se generó el lockfile) y comprobé que
`pnpm install --frozen-lockfile` funciona. Pedí a Agente 1 que cambie el comando
de docker-compose para usar ese install congelado.
