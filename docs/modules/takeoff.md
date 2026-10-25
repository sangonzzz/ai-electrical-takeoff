# Module: takeoff

Owner: Agente 1.

## What it does

`compute_takeoff(rooms, detections) -> Takeoff` aggregates active detections into
per-room rows, sheet totals, and an unassigned bucket.

## Algorithm

1. Skip `status == "deleted"`.
2. For each remaining detection, increment both `category` and
   `category.subtype` keys.
3. If `room_id` matches a known room → that room's row; else → `unassigned`.
4. Unassigned detections still increment `totals` (every active mark counts).

## Known limits

- Does not validate that subtype matches category (Pydantic does that on
  `Detection` construction).
- Room order follows the input `rooms` list.
