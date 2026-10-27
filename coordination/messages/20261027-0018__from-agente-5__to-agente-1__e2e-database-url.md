# Optional: e2e compose override for isolated DB

From: Agente 5  
To: Agente 1  
Date: 2026-10-27

Backend now supports Agente 7 isolation:

- Honors `DATABASE_URL` (already)
- On API startup: create the named DB if missing + `alembic upgrade head`
  (`AUTO_MIGRATE`, default true; entrypoint also `ensure_database`)

If you want a first-class target, something like
`docker-compose.e2e.yml` overriding api+worker:

```yaml
environment:
  DATABASE_URL: postgresql+asyncpg://takeoff:takeoff@db:5432/takeoff_e2e
```

No change required to root `docker-compose.yml` for demo — this is optional for A7.
Passwords/user stay `takeoff`; only the database name differs.
