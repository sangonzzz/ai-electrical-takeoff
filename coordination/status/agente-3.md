# Agente 3 — Rooms

## Estado

Mech. Closet only for KEYNOTES with WATER HEATER / TANK / PANEL / MECHANICAL.

## Hecho

- KEYNOTES table parse: tag → description; Mech. Closet only if desc matches
  WATER HEATER, TANK, PANEL, or MECHANICAL (B14 yes; A01 range no).
- Plan 3: no `Mech. Closet (A01)`; range `gfci_240v` @ (978.3, 401.4) →
  Kitchen / Dining; all 4 plans keep `Mech. Closet (B14)`.
- Message Agente 7 to refresh golden.

## Room lists (display_name)

**Plan 1:** Attic, Bath, Bedroom / Studio, CL 1, CL 2, Exterior, Kitchen / Dining, Laundry, Living, Mech. Closet (B14)

**Plan 2:** Attic, Bath, Bed 1, Bed 2, CL 1, CL 2, Dining, Exterior, Hallway, Kitchen, Laundry, Living, Mech. Closet (B14)

**Plan 3:** Attic, Bath 1, Bath 2, Bed 1, Bed 2, CL 1, CL 2, CL 3, CL 4, Exterior, Hall, Kitchen / Dining, Laundry, Living, Mech. Closet (B14)

**Plan 4:** Attic, Bath 1, Bath 2, Bed 1, Bed 2, CL 1, CL 2, Exterior, Hallway, Kitchen, Laundry, Living, Mech. Closet (B14), Optional Bed 3, Walk-In Closet

## Cómo probarlo

```bash
uv run pytest engine/tests/rooms/test_rooms.py::test_plan3_a01_range_not_mech_closet \
  engine/tests/rooms/test_rooms.py::test_all_plans_keep_mech_closet_b14 -v
```

## Siguiente

- Agente 7 golden refresh; Agente 1 version bump if needed for this rooms delta.

## Bloqueos

- Plan 3 half-hot count vs golden still Agente 2 (if not yet restored).

## Decisions

1. Mech. Closet keynote filter = KEYNOTES description regex
   `WATER HEATER|TANK|PANEL|MECHANICAL`.
2. Non-mech kitchen appliance keynotes (RANGE/OVEN) merge into Kitchen.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

A01 en el plan 3 es la cocina (range) según la tabla KEYNOTES, no un closet.
Solo convertimos un hueco en `Mech. Closet` si la descripción del keynote habla
de WATER HEATER, TANK, PANEL o MECHANICAL (como B14). A01 ya no crea habitación;
el 240V del range queda en Kitchen / Dining. Los cuatro planos siguen teniendo
Mech. Closet (B14). Pedí a Agente 7 que refresque el golden.
