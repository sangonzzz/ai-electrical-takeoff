# Agente 1 — Lead / architecture / integration

## Estado

**v0.6.0** tagged — motor final congelado.

## Hecho

- `PIPELINE_VERSION` → `0.6.0` + CHANGELOG + tag
- AGENTS.md / DECISIONS / README: freeze final en 0.6.0
- Mensaje to-all

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.0
git show v0.6.0 --no-patch
```

## Siguiente

- Solo backend / frontend / eval docs salvo OK de Santiago para engine
- Rebuild api/worker: `docker compose up -d --build api worker`

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Engine final = v0.6.0 (freeze reforzado).

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Marqué el motor en **0.6.0** como versión final de la demo. A partir de aquí nadie toca detección, cuartos, LLM, cables/BOM u overlay sin tu visto bueno. El backend, el front y la documentación de eval pueden seguir. El tag `v0.6.0` está en GitHub.
