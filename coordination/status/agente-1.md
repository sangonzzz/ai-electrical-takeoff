# Agente 1 — Lead / architecture / integration

## Estado

**v0.6.2** tagged — engine frozen after this.

## Hecho

- `PIPELINE_VERSION` → `0.6.2` + CHANGELOG + tag
- AGENTS / DECISIONS / README: freeze at 0.6.2
- Mensaje to-all

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.2
git show v0.6.2 --no-patch
```

## Siguiente

- Solo backend / frontend / eval docs salvo OK de Santiago para engine

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Engine frozen at v0.6.2.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Parche **0.6.2** y desde aquí el motor queda congelado otra vez: nadie cambia detección/cuartos/LLM/BOM/overlay sin tu OK. El tag está en GitHub.
