# Agente 1 — Lead / architecture / integration

## Estado

v0.3.1: compose web arreglado (VITE_API_BASE_URL + volúmenes node_modules); pipeline 0.3.1.

## Hecho

- `docker-compose.yml` web: `VITE_API_BASE_URL`, anonymous `/app/node_modules` + `.pnpm-store`
- `PIPELINE_VERSION` → `0.3.1` (A2/A8 behavior after 0.3.0)
- CHANGELOG v0.3.1; `docker compose config` OK

## Cómo probarlo

```bash
docker compose config
uv run takeoff --version   # -> 0.3.1
docker compose up -d web   # should stay up on Windows Docker Desktop
```

## Siguiente

- Confirmar con Santiago que el contenedor `web` ya no sale
- Pushear CI cuando haya scope `workflow`

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Ninguna nueva (sigue ENGINE=real; bump patch por cambios A2/A8).

## Needs from Santiago

- Probar `docker compose up` y confirmar que `web` responde en :5173

## Explicación para Santiago

El contenedor del front se caía en Windows porque montábamos tu carpeta `web` completa, incluidos los `node_modules` de Windows, dentro de Linux. Ahora el contenedor instala sus propios módulos Linux en un volumen aparte. También corregí el nombre de la variable de la API (`VITE_API_BASE_URL`). Subí la versión del motor a `0.3.1` porque agentes 2 y 8 ya cambiaron el comportamiento después de `0.3.0`, así el backend no reutiliza análisis viejos.
