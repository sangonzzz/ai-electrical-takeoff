# Agente 1 — Lead / architecture / integration

## Estado

**v0.6.3** tagged — engine frozen after this.

## Hecho

- `PIPELINE_VERSION` → `0.6.3` + CHANGELOG (wires restore v0.6.0 + B38 + 3-way) + tag
- AGENTS / DECISIONS / README: freeze at 0.6.3
- Mensaje to-all

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.3
git show v0.6.3 --no-patch
```

## Siguiente

- Solo backend / frontend / eval docs salvo OK de Santiago para engine

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Engine frozen at v0.6.3 (wires restored to v0.6.0 geometry + B38 exclusion + 3-way → nm_14_3).

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Parche **0.6.3**: el cableado vuelve a la geometría buena de v0.6.0, más exclusión de B38/keynote y la regla de 3-way → 14/3. Desde aquí el motor queda congelado otra vez; nadie cambia detección/cuartos/LLM/BOM/overlay sin tu OK. El tag está en GitHub.
