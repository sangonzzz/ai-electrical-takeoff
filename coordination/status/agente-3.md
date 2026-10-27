# Agente 3 — Rooms

## Estado

Unlabeled-pocket rule tightened (no Plan 1 false Exterior rooms).

## Hecho

- Labels, wall mask, open-plan, Attic panel, assign_room, Laundry display.
- **Tightened unlabeled pockets:** deep interior hole (≥8 pt inside footprint) +
  area ≥ 9 sq ft @ 18 pt/ft; keynote only if tag bbox fully inside pocket;
  smaller deep holes merge into nearest labeled room (WH closet → Bath).
- Plan 1: removed false `Unlabeled space 1` and `Mech. Closet (B32)`.
- Messages: Agente 7 (refresh golden), Agente 1 (bump version + DECISIONS).

## Room lists (display_name) after tighten

**Plan 1:** Laundry, Bath, Kitchen / Dining, CL 1, Living, Bedroom / Studio, CL 2, Attic, Exterior

**Plan 2:** CL 1, CL 2, Laundry, Dining, Kitchen, Hallway, Bed 1, Living, Bath, Bed 2, Attic, Exterior

**Plan 3:** CL 1, CL 2, Bed 2, Bed 1, Laundry, Hall, Bath 2, Bath 1, CL 3, Kitchen / Dining, Living, CL 4, Attic, Exterior

**Plan 4:** Bed 2, Kitchen, Bath 2, Living, Hallway, CL 1, Laundry, CL 2, Walk-In Closet, Bath 1, Optional Bed 3, Bed 1, Unlabeled space 1, Unlabeled space 2, Attic, Exterior

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/rooms/ -v
```

Sanity Plan 1:

- ~(1150, 183) outdoor unit → Exterior
- ~(1330, 170) B32 niche → Exterior
- ~(1324, 237) WH closet → Bath (merged, not Exterior / not Mech. Closet)
- ~(1000, 780) → Exterior

## Siguiente

- Agente 1 bump + DECISIONS.
- Agente 7 golden refresh.

## Bloqueos

- Ninguno.

## Decisions

1. Open-plan: Voronoi euclidiano.
2. Attic = gray-stroke panel.
3. `LNDRY` → `Laundry`.
4. **Unlabeled pockets (tightened):** deep footprint hole + ≥9 sq ft @ 18 pt/ft;
   Mech. Closet only if keynote bbox fully inside; else Unlabeled space N;
   smaller deep holes merge into nearest labeled room. Exterior = outside footprint
   only (perimeter niches stay Exterior).

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Antes, huecos pequeños fuera de la casa (unidad exterior B38, nota B32 en el muro)
salían como habitaciones falsas. Ahora solo contamos huecos **bien adentro** del
edificio, de al menos 9 sq ft, y un keynote solo nombra el closet si el texto está
dentro del hueco (no en el muro). El closet del water heater es más chico: se une
al baño más cercano, no a Exterior. Pedí a Agente 7 que refresque el golden y a
Agente 1 que suba la versión.
