# Agente 3 — Rooms

## Estado

Final pocket rule: Mech. Closet (B14) on all plans; never Unlabeled space.

## Hecho

- Replaced tightened pocket rule with:
  1. Deep hole + keynote within ~14 pt → `Mech. Closet (<tag>)` any size
  2. Deep + `240V` text (no keynote) → `Mech. Closet (B14)` (plans 2/3 off-viewport)
  3. Other deep holes → merge longest shared boundary (+ nearer label ≤75 pt)
  4. Shallow perimeter niches → Exterior (B38 outdoor unit)
  5. Never emit `Unlabeled space`
- Acceptance tests for Plan 1 exact rooms, B14 WH, all-plans Mech B14, Plan 4
  Bath2/Hallway, detection counts (1/2/4 vs golden; plan 3 classify gap noted).
- Messages: Agente 7 (golden refresh), Agente 1 (version bump), Agente 2
  (restore plan 3 `afci_half_hot`).

## Room lists (display_name)

**Plan 1:** Attic, Bath, Bedroom / Studio, CL 1, CL 2, Exterior, Kitchen / Dining, Laundry, Living, Mech. Closet (B14)

**Plan 2:** Attic, Bath, Bed 1, Bed 2, CL 1, CL 2, Dining, Exterior, Hallway, Kitchen, Laundry, Living, Mech. Closet (B14)

**Plan 3:** Attic, Bath 1, Bath 2, Bed 1, Bed 2, CL 1, CL 2, CL 3, CL 4, Exterior, Hall, Kitchen / Dining, Laundry, Living, Mech. Closet (A01), Mech. Closet (B14)

**Plan 4:** Attic, Bath 1, Bath 2, Bed 1, Bed 2, CL 1, CL 2, Exterior, Hallway, Kitchen, Laundry, Living, Mech. Closet (B14), Optional Bed 3, Walk-In Closet

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/rooms/ -v
```

Sanity:

- Plan 1 WH `(1322.2, 222.1)` → Mech. Closet (B14)
- Plan 1 outdoor `(1150, 183)` / B32 `(1330, 170)` → Exterior
- Plan 4 Hallway owns SD/MA + 3D switch; Bath 2 owns GFI @ `(1491, 210)`
- No `Unlabeled space` on any plan

## Siguiente

- Agente 2 restores plan 3 half-hot → detection counts match golden.
- Agente 7 refreshes golden; Agente 1 bumps PIPELINE_VERSION.

## Bloqueos

- Plan 3 missing `afci_half_hot` @ ~(895.8, 505.68) vs golden v0.6.4 — Agente 2
  (classify); rooms never add/remove detections.
- Plan 4 B14 closet has 240V text inside the room polygon, but the nearby FC
  receptacle still assigns to Kitchen (symbol placement / subtype — Agente 2).

## Decisions

1. Open-plan: Voronoi euclidiano.
2. Attic = gray-stroke panel.
3. `LNDRY` → `Laundry`.
4. **Pockets (final):** deep keynote → Mech. Closet; deep 240V fallback → B14;
   else longest-boundary merge (nearer label ≤75 pt when competing); shallow →
   Exterior; never Unlabeled space.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Cambié la regla de los huecos sin etiqueta. Si hay un keynote (B14) cerca del
hueco — aunque el texto esté sobre el muro — ese hueco es `Mech. Closet (B14)`,
aunque sea chico. Si no hay keynote pero sí un texto `240V` (plans 2/3 donde B14
está fuera del viewport eléctrico), también lo llamamos Mech. Closet (B14). El
resto de huecos interiores se pegan a la habitación vecina con más pared en
común; nunca salen como “Unlabeled space”. Los huecos del borde (unidad exterior
B38) quedan Exterior. Pedí a Agente 2 que recupere un receptáculo half-hot que
falta en el plan 3 (no es cosa de rooms), a Agente 7 el golden nuevo, y a Agente 1
la versión.
