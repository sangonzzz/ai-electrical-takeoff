# From Agente 7 → Agente 5: please add ground-truth export

Eval now treats human review in the app as the primary ground truth.

## Requested endpoint

`GET /api/sheets/{sheet_id}/ground-truth.json`

Return the **current** (reviewed) active detections in a shape eval already loads
(see `docs/modules/evaluation.md` and `eval/io_truth.py`):

```json
{
  "schema_version": "1.0.0",
  "source": "human_review",
  "endpoint": "GET /api/sheets/{id}/ground-truth.json",
  "sheet_id": "<id>",
  "page_index": 0,
  "plan": 1,
  "exported_at": "<iso8601>",
  "analysis_run_id": "<current run id>",
  "detections": [
    {
      "id": "...",
      "category": "light",
      "subtype": "recessed",
      "center": { "x": 0, "y": 0 },
      "bbox": { "x0": 0, "y0": 0, "x1": 0, "y1": 0 },
      "room_id": "...",
      "room_name": "Living",
      "codes": [],
      "status": "active"
    }
  ],
  "corrections": [ /* same objects as GET /corrections for this sheet/run */ ],
  "counts": { /* optional: room_name -> category.subtype -> int from compute_takeoff */ }
}
```

Notes:

- Include only `status == "active"` in `detections` (or mark deleted; eval skips them).
- `room_name` should be the room `display_name` (Agente 3).
- `plan` = `page_index + 1` for the Escondido demo.
- Santiago will save the response as `eval/ground_truth/planN.detections.json`.

Existing `GET /api/sheets/{id}/corrections` is already enough for
`planN.corrections.json` if you prefer not to embed corrections.
