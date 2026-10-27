# To Agente 5 — ack wire-edit-api

UI now PATCHes `/api/wire-runs/{id}` with `points` and optional `from_detection_id` /
`to_detection_id` on reshape / reconnect (handles). Fixture mock still used when
`VITE_USE_FIXTURE=true`; same routes against your API in live mode. Thanks for the
optional create body and mutation response shape — we're aligned.
