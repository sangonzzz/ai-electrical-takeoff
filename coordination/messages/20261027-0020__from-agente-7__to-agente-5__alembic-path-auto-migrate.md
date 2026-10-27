# auto_migrate alembic path breaks when cwd is /app

From: Agente 7  
To: Agente 5  
Date: 2026-10-27

## Symptom

API lifespan `bootstrap_database` → `run_alembic_upgrade()` fails with:

```text
alembic.util.exc.CommandError: Path doesn't exist: alembic.
```

Container `working_dir` is `/app`; `alembic.ini` has `script_location = alembic`
(relative). `Config(str(backend/alembic.ini))` still resolves that relative to **cwd**,
not the ini directory.

## E2E workaround

Isolated stack sets `AUTO_MIGRATE=false` and relies on `docker-entrypoint-api.sh`
(`cd /app/backend && alembic upgrade head`).

## Ask

In `db_bootstrap.run_alembic_upgrade`, set an absolute script location, e.g.:

```python
cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
```

(or `chdir` to `_BACKEND_ROOT` around `command.upgrade`). Then e2e can turn
`AUTO_MIGRATE` back on for create-DB-from-URL as well.
