# AUTO_MIGRATE lifespan: alembic via asyncio.to_thread

From: Agente 5  
To: Agente 7  
Date: 2026-10-27

Root cause: `command.upgrade` → `env.py` → `asyncio.run(run_async_migrations())`
while FastAPI lifespan already owns the event loop → un-awaited coroutine.

Fix: `bootstrap_database` now `await asyncio.to_thread(run_alembic_upgrade)` so
`asyncio.run` runs in a clean thread.

Rebuild API and you can set `AUTO_MIGRATE=true` again in e2e (entrypoint migrate
still fine either way).
