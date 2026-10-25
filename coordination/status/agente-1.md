# Agente 1 — Lead / architecture / integration

## Estado

Scaffold completo y pusheado a `main`. Listo para agentes 2–8.

## Hecho

- Repo privado https://github.com/sangonzzz/ai-electrical-takeoff (`main`)
- Identidad local `sangonzzz` / `santiagonzalezmora@gmail.com`
- `docs/SPEC.md`, PDF en `data/plans/escondido_plans.pdf`
- uv workspace Python 3.12 (`engine` + `backend`), `uv.lock`
- Contratos completos: `models.py`, `types.py`, `takeoff.py`, `config.py`, `pdf_context.py`, `cli.py`
- Stubs con firmas exactas para agentes 2–8
- Fixtures + `contracts/schema.json` + `web/src/types/contracts.ts`
- docker-compose, Makefile, coordination (DECISIONS, status, mensaje to-all)
- Verificado: `uv run pytest` (5 passed), `uv run takeoff --help`, `docker compose config`

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest
uv run takeoff --help
uv run takeoff schema
docker compose config
```

## Siguiente

- Cuando Santiago dé scope `workflow` al token `gh`, pushear `.github/workflows/ci.yml`
- Integrar cuando Agente 2 entregue `analyze_sheet`

## Bloqueos

- Push de GitHub Actions CI requiere `gh auth refresh -h github.com -s workflow` (el token actual no tiene scope `workflow`). El archivo está en el working tree local.

## Decisions

Ver `coordination/DECISIONS.md`. Extra: push inicial es un commit limpio sin trailer Co-authored-by (Cursor lo inyectaba en `git commit`); historial granular queda en rama local `scaffold-detailed`.

## Needs from Santiago

- Correr: `gh auth refresh -h github.com -s workflow,repo,read:org,gist` y avisar para pushear el CI.
- `ANTHROPIC_API_KEY` en `.env` cuando se pruebe LLM (Agente 4).

## Explicación para Santiago

Armé la base del proyecto para que los otros siete agentes trabajen en paralelo sin pisarse.
Los contratos Pydantic (`models.py`) definen exactamente qué es una detección, un cuarto, un takeoff, etc.
`pdf_context` lee el PDF vectorial y separa trazos negros/grises y texto — sin eso nadie puede detectar símbolos.
`compute_takeoff` es la única función que cuenta; el frontend tendrá que mirarla igual.
Dejé stubs (`NotImplementedError`) con las firmas correctas para que cada agente sepa qué implementar.
También dejé Docker, Makefile y el protocolo de mensajes en `coordination/`.
El repo privado ya está en GitHub bajo tu cuenta `sangonzzz` (falta autorizar scope `workflow` para subir el CI).
