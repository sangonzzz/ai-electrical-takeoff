# Agente 1 — Lead / architecture / integration

## Estado

**v1.0.5** tagged locally — `PIPELINE_VERSION` still **0.6.7** (no push; Agente 9).

## Hecho

- A6 UI polish commit; scope web/coordination only
- Web: tsc + vitest 36 + build OK; package.json 1.0.5
- CHANGELOG + README; tag `v1.0.5`; to-all

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.7
git show v1.0.5 --no-patch
```

## Siguiente

- Agente 9 push main + tag `v1.0.5`

## Bloqueos

- (ninguno)

## Decisions

UI-only app tags without PIPELINE bump.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

App **v1.0.5**: un solo botón clear en la búsqueda y sin rayas largas (em dash)
en el copy. Motor 0.6.7. Tag local; Agente 9 hace push.
