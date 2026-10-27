# Agente 3 — Rooms

## Estado

Attic polygon fijo (panel gray-stroke); display `Laundry`; M1–M4 OK.

## Hecho

- Labels + wall mask + polígonos + `assign_room` / `assign_rooms`.
- `LNDRY` → display `Laundry` (`name` raw).
- **Attic:** polígono desde el marco gray-stroke del panel (~y 419–452 en Plan 1),
  no desde el texto padded. Plan 1 Attic = 1 light + 1 switch.
- Tests: `engine/tests/rooms/` (16).
- Docs: `docs/modules/rooms.md`.
- Pedido bump de `PIPELINE_VERSION` a Agente 1.

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/rooms/ -v
```

Sanity:

- ~(1275, 506) → Bedroom / Studio; ~(1000, 780) → Exterior
- ~(1120, 409) **no** Attic; ~(1136, 444) **sí** Attic
- Plan 1 Attic: exactamente 1 light y 1 switch

## Siguiente

- Agente 1 bump de versión.
- Agente 7 (si falta) templates CL Plan 3/4.

## Bloqueos

- Ninguno.

## Decisions

1. Open-plan: Voronoi euclidiano.
2. Attic panel = gray stroke rect (fills first if present); padded text solo fallback.
3. `LNDRY` → `Laundry`.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

El cajón “IN ATTIC” del plano es un rectángulo dibujado con líneas grises, no un relleno.
Antes usábamos un recuadro alrededor del texto y quedaba ~12 pt más arriba: el plafón del
pasillo entraba en Attic y el interruptor de abajo se iba a Living. Ahora el polígono
Attic sigue exactamente ese marco del panel. En Plan 1 Attic tiene exactamente una luz
y un interruptor. Pedí a Agente 1 que suba la versión del pipeline para que el backend
vuelva a analizar.
