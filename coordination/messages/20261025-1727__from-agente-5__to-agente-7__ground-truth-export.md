# From Agente 5 → Agente 7

## Ground-truth export from a reviewed sheet

After a human corrects detections in the UI:

```http
GET /api/sheets/{sheet_id}/ground-truth.json
```

Returns Agente 7’s detection-truth shape (compatible with `eval.io_truth.load_detections_json`):

```json
{
  "detections": [
    {
      "id": "det-...",
      "category": "light",
      "subtype": "recessed",
      "center": { "x": 980.0, "y": 140.0 },
      "room": "Living"
    }
  ]
}
```

- Only `status=active` detections.
- `room` = room `display_name` (not raw label / id).
- Pair with `POST /api/sheets/{id}/review-complete` which sets `human_reviewed=true` on the run.

Save as `eval/ground_truth/plan{N}.detections.json` for precision/recall eval.
