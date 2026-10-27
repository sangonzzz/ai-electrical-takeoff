# Agente 1 — Lead / architecture / integration

## Estado

**v0.6.1** tagged (patch). Freeze policy unchanged.

## Hecho

- `PIPELINE_VERSION` → `0.6.1` + CHANGELOG + tag + README

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.1
git show v0.6.1 --no-patch
```

## Siguiente

- Rebuild api/worker if needed: `docker compose up -d --build api worker`

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Ninguna nueva.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Parche **0.6.1** para que el backend no reutilice análisis de 0.6.0 si el motor ya cambió después. El freeze sigue: más cambios de engine solo con tu OK.
