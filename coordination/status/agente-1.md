# Agente 1 — Lead / architecture / integration

## Estado

Scaffold completo: contratos, pdf_context, CLI, infra, repo privado listo para agentes 2–8.

## Hecho

- Repo privado `sangonzzz/ai-electrical-takeoff` en `main`, identidad local `sangonzzz`
- `docs/SPEC.md`, PDF en `data/plans/escondido_plans.pdf`
- uv workspace (`engine` + `backend`), lock + sync
- `models.py`, `types.py`, `takeoff.py`, `config.py`, `pdf_context.py`, `cli.py` completos
- Stubs con firmas exactas para módulos de agentes 2–8
- Fixtures `contracts/fixtures/*`, schema export, tipos TS
- docker-compose, Makefile, CI, coordination

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest
uv run takeoff --help
uv run takeoff schema
docker compose config
```

## Siguiente

- Integrar pipeline cuando Agente 2 entregue `analyze_sheet`
- Regenerar schema/TS si cambian contratos (anunciar en messages)
- Push continuo de `main` cuando otros agentes pidan sync

## Bloqueos

Ninguno para el scaffold.

## Decisions

Ver `coordination/DECISIONS.md` (reglas de conteo + email git + unassigned en totals).

## Needs from Santiago

- Scope `user` en `gh` si quiere usar `gh api user/emails` (ahora usamos el email público del perfil).
- `ANTHROPIC_API_KEY` en `.env` cuando se pruebe LLM (Agente 4).

## Explicación para Santiago

Armé la base del proyecto para que los otros siete agentes trabajen en paralelo sin pisarse.
Los contratos Pydantic (`models.py`) definen exactamente qué es una detección, un cuarto, un takeoff, etc.
`pdf_context` lee el PDF vectorial y separa trazos negros/grises y texto — sin eso nadie puede detectar símbolos.
`compute_takeoff` es la única función que cuenta; el frontend tendrá que mirarla igual.
Dejé stubs (`NotImplementedError`) con las firmas correctas para que cada agente sepa qué implementar.
También dejé Docker, Makefile, CI y el protocolo de mensajes en `coordination/`.
El repo privado ya está en GitHub bajo tu cuenta `sangonzzz`.
