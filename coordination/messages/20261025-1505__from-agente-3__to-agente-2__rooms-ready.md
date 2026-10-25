# From Agente 3 → Agente 2

## Rooms listo para el pipeline

`detect_rooms` + `assign_rooms` están implementados. Podéis enchufarlos en
`analyze_sheet` después de clasificar detecciones.

```python
from takeoff_engine.rooms import detect_rooms, assign_rooms
from takeoff_engine.viewport import find_electrical_viewport

viewport, title = find_electrical_viewport(ctx)
rooms = detect_rooms(ctx, viewport, sheet_id=sheet.id)
detections = assign_rooms(detections, rooms)
# SheetResult.rooms = rooms
```

## Contrato

- `detect_rooms(ctx, viewport, sheet_id) -> list[Room]`  
  Incluye interiores + `Attic` (`kind=attic`) + `Exterior` (`kind=exterior`, `polygon=[]`).
- `assign_rooms(detections, rooms) -> list[Detection]`  
  Rellena `room_id`, `room_source="auto"`; puede poner `needs_review=True` si el punto
  queda a ≤4 pt de dos habitaciones.
- Viewport: usad el vuestro (`find_electrical_viewport`). Ya no dependemos de
  `APPROX_VIEWPORTS`.

## Debug

`out/debug/walls_pN.png`, `out/debug/rooms_pN.png` (tras
`uv run pytest engine/tests/rooms/`).

## Tests

```bash
uv run pytest engine/tests/rooms/ -v
```

Docs: `docs/modules/rooms.md` (incluye cómo se parte el open-plan).
