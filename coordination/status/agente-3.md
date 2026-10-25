# Agente 3 — Rooms

## Estado

M1–M4 listos; `display_name` alineado con eval (`LNDRY` → `Laundry`).

## Hecho

- `engine/takeoff_engine/rooms.py`: labels, wall mask, polígonos, assign.
- Alias de display: raw `LNDRY` → `display_name` `"Laundry"` (`name` sigue `LNDRY`).
- Tests: `engine/tests/rooms/` (incluye `test_lndry_display_is_laundry`).
- Debug: `out/debug/walls_pN.png`, `out/debug/rooms_pN.png`.
- Docs: `docs/modules/rooms.md`.
- Viewport: `find_electrical_viewport` (Agente 2).
- Mensaje a Agente 7: listas exactas de `display_name` por plan; Plans 3–4 tienen más
  `CL` que el template (`CL 1`… vs un solo `CL`).

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/rooms/ -v
# Ver out/debug/walls_p1.png y out/debug/rooms_p1.png
```

Sanity SPEC / eval:

- Punto ~(1275, 506) página 1 → `Bedroom / Studio`
- Punto ~(1000, 780) → `Exterior`
- Página 2: `Kitchen` y `Dining` separadas
- Label `LNDRY` → display `Laundry`

## Siguiente

- Agente 7 actualiza templates Plan 3/4 (CL numerados).
- Integración pipeline (Agente 2) / backend move (Agente 5) ya avisados.

## Bloqueos

- Ninguno.

## Decisions

1. Open-plan: Voronoi euclidiano en la región compartida.
2. Plan 3/4: más `CL` en el PDF que SPEC/templates; numeramos todos; Agente 7 debe
   actualizar ground truth.
3. `LNDRY` → display `Laundry` para match con eval.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Detecto habitaciones del plano eléctrico: etiquetas en negrita, paredes rasterizadas con
puertas cerradas, flood-fill desde cada nombre, y en espacios abiertos parto por la
etiqueta más cercana. `LNDRY` en el PDF se muestra como **Laundry** (el nombre crudo
sigue siendo LNDRY). Attic es el cajón “IN ATTIC”; fuera del edificio es Exterior.
`assign_room` dice a qué habitación pertenece un punto. En Plan 3 hay cuatro closets
(CL 1–4) y en Plan 4 dos; se lo pedí a Agente 7 para que el eval coincida.
