# Agente 1 — Lead / architecture / integration

## Estado

Docker api/worker usan imagen con `/opt/venv` (ya no `uv sync` sobre el `.venv` del host). Engine sigue en **0.4.0** (freeze).

## Hecho

- `backend/Dockerfile` + `docker-entrypoint-api.sh` (alembic solo en api)
- Compose: api/worker → `takeoff-backend:local`; volúmenes solo `storage/` y `.cache/`
- Worker: `arq app.worker.WorkerSettings`, `restart: unless-stopped` + healthcheck
- `.dockerignore` excluye `.venv` / `node_modules` / etc.
- Engine **no** tocado (freeze 0.4.0)

## Cómo probarlo

```bash
docker compose config
docker compose up -d --build
docker compose ps
# api :8000 /health · web :5173 · worker Up
```

## Siguiente

- Confirmar con Santiago que el `.venv` de Windows ya no se corrompe
- Pushear CI cuando haya scope `workflow`

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Imagen compartida api/worker; venv solo en `/opt/venv` dentro de la imagen.

## Needs from Santiago

- `docker compose up -d --build` y confirmar 5 servicios Up

## Explicación para Santiago

Antes api y worker instalaban dependencias al arrancar en la misma carpeta `.venv` que usás en Windows, a la vez, y se pisaban. Ahora se **construye una imagen** una vez con el entorno Linux en `/opt/venv` dentro del contenedor; al arrancar solo migran la DB (api) y levantan uvicorn/arq en segundos. Solo montamos `storage/` y `.cache/` — nunca el repo completo encima del venv. El motor sigue congelado en 0.4.0.
