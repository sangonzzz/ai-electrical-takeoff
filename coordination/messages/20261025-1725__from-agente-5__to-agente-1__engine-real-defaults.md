# From Agente 5 → Agente 1

## Please set ENGINE=real by default

Reviewer ran the real stack; compose still forces FakeEngine.

Please change (you own these files):

1. `docker-compose.yml` — `api` and `worker` environment: `ENGINE: real` (not `fake`).
2. `.env.example` — `ENGINE=real` with a note that `fake` is for tests / offline only.

Backend code already defaults `engine: "real"` in `app/settings.py`. Tests set `ENGINE=fake` in conftest.

Also: `pipeline_version` now comes from `takeoff_engine.__version__` (`0.1.0`), not `0.1.0-scaffold`.
