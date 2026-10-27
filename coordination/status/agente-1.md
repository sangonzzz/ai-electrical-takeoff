# Agente 1 — Lead / architecture / integration

## Estado

**v0.6.6** tagged — engine frozen after this.

## Hecho

- `PIPELINE_VERSION` → `0.6.6` + CHANGELOG + DECISIONS (closet + longest-boundary merge)
- AGENTS / README: freeze at 0.6.6
- Mensaje to-all; ack Agente 3

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.6
git show v0.6.6 --no-patch
```

## Siguiente

- Agente 7 golden refresh (may still wait on plan-3 half-hot / Santiago)
- Solo backend / frontend / eval docs salvo OK de Santiago para engine

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Engine frozen at v0.6.6. Closet + merge rules in DECISIONS Rooms §5.

## Needs from Santiago

- (ninguno for this bump)

## Explicación para Santiago

Parche **0.6.6**: el closet mecánico B14 se nombra bien (keynote cerca o 240V sin
tag), los otros huecos se fusionan al vecino con más borde compartido, y ya no
salen “Unlabeled space”. Motor congelado otra vez.
