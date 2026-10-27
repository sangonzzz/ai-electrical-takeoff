# Agente 1 — Lead / architecture / integration

## Estado

**v0.6.4** tagged — engine frozen after this.

## Hecho

- `PIPELINE_VERSION` → `0.6.4` + CHANGELOG + DECISIONS (B14 closet / unlabeled interior)
- AGENTS / README: freeze at 0.6.4
- Mensaje to-all; ack Agente 3

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.4
git show v0.6.4 --no-patch
```

## Siguiente

- Inbox: Agente 2 still requesting patch for Plan 1 disposal `$` restore (not in 0.6.4)
- Solo backend / frontend / eval docs salvo OK de Santiago para engine

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Engine frozen at v0.6.4. Unlabeled interior pockets + B14 → Mech. Closet (see DECISIONS Rooms §5).

## Needs from Santiago

- (ninguno) — confirm if Agente 2 disposal-switch bump should be 0.6.5

## Explicación para Santiago

Parche **0.6.4**: el closet del water heater (keynote B14) y otros huecos sin etiqueta
dentro del edificio ya no van a Exterior; se llaman Mech. Closet (B14) o Unlabeled space N.
Motor congelado otra vez. Queda pendiente el bump del switch de disposal (Agente 2)
si lo apruebas como 0.6.5.
