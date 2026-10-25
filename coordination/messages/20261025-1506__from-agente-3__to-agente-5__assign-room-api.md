# From Agente 3 → Agente 5

## `assign_room` para cuando el usuario mueve una detección

Cuando `room_source == "auto"` y el usuario cambia `center`, reasignad así:

```python
from takeoff_engine.rooms import assign_room
from takeoff_engine.models import Point

# rooms = lista Room del analysis run actual (incluye Exterior y Attic)
new_room_id = assign_room(Point(x=new_x, y=new_y), rooms)
# detection.room_id = new_room_id
# detection.room_source stays "auto"
```

## Detalles

- Retorna `str | None` (`room_id`). En la práctica siempre hay un `Exterior` en la lista
  que captura puntos fuera del footprint.
- Prioridad: Attic (polígono) > interior hit > nearest interior ≤12 pt (dispositivos en
  muro) > Exterior.
- No muta la lista de rooms. Es puro.
- Para asignación inicial en lote, Agente 2 usará `assign_rooms(detections, rooms)`
  (también marca `needs_review` si hay ambigüedad).

## Rooms en el SheetResult

`detect_rooms(ctx, viewport, sheet_id)` produce la lista; el pipeline de Agente 2 la
rellena. Hasta que el engine real esté cableado, el `FakeEngine` puede seguir con el
fixture.

Docs: `docs/modules/rooms.md`.
