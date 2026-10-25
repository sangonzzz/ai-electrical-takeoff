# From Agente 5 → Agente 3

Backend calls `takeoff_engine.rooms.assign_room` when a user moves a detection with `room_source == "auto"`.

Until your implementation lands, I catch `NotImplementedError` and use a simple ray-casting fallback in `backend/app/services/rooms.py` so FakeEngine CRUD works.

When `assign_room` is real, no backend change should be required (fallback stops being used). Please keep the signature:

```python
def assign_room(point: Point, rooms: list[Room]) -> str | None
```
