# Agente 1 — Lead / architecture / integration

## Estado

**v0.6.5** tagged — engine frozen after this.

## Hecho

- `PIPELINE_VERSION` → `0.6.5` + CHANGELOG (pocket rule + prices + cable-edit response)
- DECISIONS Rooms §5 tightened pocket rule; AGENTS / README freeze at 0.6.5
- Mensaje to-all; ack Agente 3
- Noted Agente 7: golden refresh still blocked (plan 3 half-hot / plan 4 needs_review)

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.5
git show v0.6.5 --no-patch
```

## Siguiente

- Santiago: allow golden absorb of non-room deltas, or A2 restore plan3 half-hot → A7 refresh
- A2 disposal `$` still pending if not already in tree

## Bloqueos

- Golden `test_golden` expected red until refresh (A7 message 20261027-1045)
- Token `gh` sin scope `workflow` para Actions

## Decisions

Engine frozen at v0.6.5. Pocket rule tightened (see DECISIONS Rooms §5).

## Needs from Santiago

- Decision on golden refresh vs restore plan3 half-hot

## Explicación para Santiago

Parche **0.6.5**: la regla de “huecos” sin etiqueta es más estricta (solo huecos
profundos y ≥9 sq ft; keynote solo si está del todo dentro), más precios Home Depot
y el arreglo de que al editar cables la API ya no devuelve cajas/BOM viejos.
El motor queda congelado. El candado golden de Agente 7 sigue bloqueado hasta que
decidas absorber otros diffs (plan 3 half-hot) o que A2 los restaure.
