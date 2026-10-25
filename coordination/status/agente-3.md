# Agente 3 — Rooms

## Estado

M1–M4 listos: labels, wall mask, polígonos, `assign_room` / `assign_rooms`.

## Hecho

- `engine/takeoff_engine/rooms.py`: labels (lexicon + CL 1/2 + IN ATTIC), wall mask +
  cierre de puertas (swing arcs + leaves), flood fill, split open-plan por nearest label,
  Attic / Exterior, `assign_room` / `assign_rooms`.
- Tests: `engine/tests/rooms/` (13 passing).
- Debug: `out/debug/walls_pN.png`, `out/debug/rooms_pN.png`.
- Docs: `docs/modules/rooms.md`.
- Usa viewport de Agente 2 (`find_electrical_viewport`), ya no `APPROX_VIEWPORTS`.

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/rooms/ -v
# Ver out/debug/walls_p1.png y out/debug/rooms_p1.png
```

Sanity SPEC:

- Punto ~(1275, 506) en página 1 → `Bedroom / Studio`
- Punto ~(1000, 780) → `Exterior`
- Página 2: rooms `Kitchen` y `Dining` separadas

## Siguiente

- Integración en `pipeline.py` (Agente 2).
- Backend llama `assign_room` al mover detecciones (Agente 5).
- Ajustar umbrales de puertas si eval muestra merges entre habitaciones.

## Bloqueos

- Ninguno.

## Decisions

1. Open-plan: split Euclidean (Voronoi) dentro de la región compartida, no geodésico.
2. Plan 3/4: el PDF tiene más labels `CL` que los listados en SPEC §1; los conservamos y
   numeramos. Pedir a Agente 1 actualizar SPEC si hace falta.
3. Exterior: polígono vacío; asignación = fuera del footprint (unión de interiores + attic).
4. Tras mensaje de Agente 2, viewport = `find_electrical_viewport` (no APPROX).

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Detecto las habitaciones del plano eléctrico en cuatro pasos. Primero leo las etiquetas
en negrita (~9.5 pt) dentro del viewport y filtro con un léxico (Living, Kitchen, CL…).
Los closets repetidos salen como CL 1, CL 2. Segundo, dibujo las paredes en una imagen
(gris de muros + líneas negras) y cierro los huecos de las puertas usando los arcos grises
de las hojas. Tercero, “inundo” desde cada etiqueta: si Living y Kitchen están en el mismo
espacio abierto, parto la zona por la etiqueta más cercana (línea imaginaria, no un muro
real). El cajón “IN ATTIC” es la habitación Attic; fuera del edificio es Exterior. Cuarto,
`assign_room` dice a qué habitación pertenece un punto (el backend lo usa si mueves un
símbolo). Todo se puede ver en `out/debug/rooms_p1.png`.
