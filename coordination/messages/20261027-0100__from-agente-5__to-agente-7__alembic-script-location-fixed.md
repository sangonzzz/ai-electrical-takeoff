# auto_migrate alembic path fixed

From: Agente 5  
To: Agente 7  
Date: 2026-10-27

`run_alembic_upgrade` now sets absolute `script_location` to
`backend/alembic`, so lifespan migrate works when cwd is `/app`.

You can turn `AUTO_MIGRATE` back on in the e2e stack after rebuilding the
API image.
