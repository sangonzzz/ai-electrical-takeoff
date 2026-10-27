# Agente 3 — Rooms

## Estado

Unlabeled interior pockets + Mech. Closet (B14); Attic panel OK; Laundry display OK.

## Hecho

- Labels, wall mask, open-plan split, Attic from gray-stroke panel, assign_room.
- `LNDRY` → display `Laundry`.
- **Unlabeled enclosed regions** inside the footprint → own interior rooms:
  keynote → `Mech. Closet (B14)`; else `Unlabeled space N`. Exterior = outside
  footprint only. Plan 1 B14 WH closet fixed.
- Tests: `engine/tests/rooms/` (incl. B14 + attic).
- Docs: `docs/modules/rooms.md`.
- Pedido bump a Agente 1 + decision para DECISIONS.md.

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/rooms/ -v
```

Sanity:

- ~(1324, 237) Plan 1 → `Mech. Closet (B14)` (not Exterior)
- ~(1000, 780) → Exterior
- ~(1120, 409) not Attic; ~(1136, 444) Attic; Attic = 1 light + 1 switch

## Siguiente

- Agente 1: bump PIPELINE_VERSION + registrar decision.
- Opcional: reducir fragmentación Unlabeled en Plans 3–4 (wall/door mask).

## Bloqueos

- Ninguno.

## Decisions

1. Open-plan: Voronoi euclidiano.
2. Attic = gray-stroke panel frame.
3. `LNDRY` → `Laundry`.
4. **Enclosed unlabeled interior pocket → own room** (`Mech. Closet (KEY)` if
   keynote nearby, else `Unlabeled space N`). Exterior only outside footprint.
   → pedir registro en `coordination/DECISIONS.md` (mensaje a Agente 1).

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

El closet del water heater en Plan 1 (keynote B14) no tiene nombre de habitación en
negrita, así que antes caía en Exterior aunque está dentro de la casa. Ahora, si hay
un hueco cerrado dentro del edificio sin etiqueta, lo convertimos en habitación: si
tiene un keynote como B14 se llama “Mech. Closet (B14)”; si no, “Unlabeled space 1”,
etc. Exterior queda solo para lo que está fuera de la casa. Pedí a Agente 1 que suba
la versión del pipeline y anote esta regla en DECISIONS.
