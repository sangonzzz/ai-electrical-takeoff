# Agente 1 — Lead / architecture / integration

## Estado

Compose web: `contracts` montado en `/contracts:ro`. Mensaje a A6 para import lazy del fixture.

## Hecho

- `docker-compose.yml` web: `./contracts:/contracts:ro` (path desde `fixture.ts`)
- Mensaje a Agente 6: dynamic import solo si `VITE_USE_FIXTURE=true`
- Engine freeze **0.4.0** intacto

## Cómo probarlo

```bash
docker compose config
docker compose up -d web --force-recreate
# Vite should resolve ../../../contracts/fixtures/sheet_result.sample.json
```

## Siguiente

- A6: lazy fixture import
- Agente 7: Accuracy results en README

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Ninguna nueva.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

El front en Docker solo montaba la carpeta `web`, pero el modo fixture importa un JSON que vive en `contracts/` (tres niveles arriba). Por eso Vite fallaba. Ahora montamos `contracts` en `/contracts` solo lectura. También pedí a Agente 6 que ese import sea lazy, para que en producción (sin fixture) no dependa de esa carpeta.
