# Attic room polygon overshoots the IN ATTIC panel (plan 1)

Agente 2 now finds the attic panel as the **gray stroke** rectangle:

`(1097.5, 419.3) – (1142.5, 452.3)` (plus ~3 pt pad in our symbol code).

Your `detect_rooms` Attic polygon on plan 1 is currently about:

`(1083.6, 405.4) – (1150.9, 442.4)`

That:

1. Includes the hallway recessed can @~(1120.3, 408.6) **above** the panel → falsely room Attic.
2. Cuts off before the panel bottom (y≈452) — our circle-with-cross @~(1117.4, 435.8) still lands inside, so we’re OK for the light, but the `$` near the bottom edge is tight.

Please tighten Attic to the gray-stroke frame (same geometry we use in `_gray_stroke_panel_around` / `_attic_boxes` in `classify.py`). No symbol change needed on our side for the light itself.
