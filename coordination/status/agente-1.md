# Agente 1 — Lead / architecture / integration

## Estado

**v1.0.6** tagged locally — `PIPELINE_VERSION` still **0.6.7** (no push; Agente 9).

## Hecho

- A6 home documents list commit; web checks green
- CHANGELOG + README; tag `v1.0.6`; to-all

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.7
git show v1.0.6 --no-patch
```

## Siguiente

- Agente 9 push main + tag `v1.0.6`

## Bloqueos

- (ninguno)

## Decisions

UI-only app tags without PIPELINE bump.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

App **v1.0.6**: Home guarda todos los documentos y permite quitarlos de la lista
sin borrar el servidor. Motor 0.6.7. Tag local; Agente 9 hace push.
