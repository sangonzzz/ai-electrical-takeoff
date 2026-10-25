# Baseline vision takeoff (v1) — LLM ONLY

This is an **evaluation baseline**, not the production pipeline. You receive a
raster image of one electrical plan sheet and a list of room names. Count
electrical components **per room** by eye.

Production detection uses vector geometry for WHERE and Claude only for WHAT.
This baseline exists so we can compare "LLM alone" vs our hybrid in demos.

## Rules

1. Return one object per provided room name (use the names exactly).
2. `counts` keys must be `category` and/or `category.subtype` from the allowed
   taxonomy (e.g. `light`, `light.recessed`, `switch.single_pole`).
3. Only count the **electrical** plan drawing if multiple plans appear on the
   sheet. Ignore mechanical/finish drawings, legends (do not count legend
   samples as devices), and the watermark.
4. Combined fixtures count once under the combined type.
5. Do **not** return coordinates or draw boxes — counts only.
6. If unsure about a room boundary, put the count in the most likely room and
   mention uncertainty in `notes`.

## Honesty

Approximate counts are expected. This baseline is intentionally weaker than the
hybrid engine; do not pretend precision you do not have.
