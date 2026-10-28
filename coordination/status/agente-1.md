# Agente 1 — Lead / architecture / integration

## Estado

**v1.0.1** app tagged — `PIPELINE_VERSION` still **0.6.7**.

## Hecho

- CHANGELOG App v1.0.1 (cable colors by type + edit handles); no pipeline bump
- README tags; mensaje to-all; tag `v1.0.1`

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.7
git show v1.0.1 --no-patch
```

## Siguiente

- Engine stays frozen at 0.6.7 unless Santiago approves

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

App tags may advance without `PIPELINE_VERSION` when analysis is unchanged.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Parche de app **v1.0.1**: los cables se colorean por tipo (14/2 vs 14/3) y al
editar aparecen handles. El motor sigue en **0.6.7**; no se reanaliza nada.
