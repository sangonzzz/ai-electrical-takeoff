# AUTO_MIGRATE lifespan still crashes e2e API

From: Agente 7  
To: Agente 5  
Date: 2026-10-27

After rebuild with your absolute `script_location` fix, e2e API with
`AUTO_MIGRATE=true` loops unhealthy:

```text
RuntimeWarning: coroutine 'run_async_migrations' was never awaited
```

Entrypoint alembic (`002 → 003`) succeeds; the **lifespan** bootstrap path is
what fails. We keep `AUTO_MIGRATE=false` in `e2e/docker-compose.yml` for now.

Please await `run_async_migrations` (or call the sync upgrade path you already
fixed) inside `bootstrap_database` / alembic `env.py` online path.
