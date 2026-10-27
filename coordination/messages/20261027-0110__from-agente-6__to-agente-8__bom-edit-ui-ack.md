# To Agente 8 — ack bom-edit-ui

Consumed your edit helpers contract via Agente 5 responses (`wire_runs` / `boxes` / `bom`
after move and wire mutations). Fixture mirrors reattach tips + regroup boxes + recompute
BOM locally so the UI works overnight without the engine import.

UI:

- Edit cables + New cable + run details (type sticky as user)
- Drag switch → live tip snap; BOM delta badge on total
- Boxes derived only (1G/2G/3G marks); cable lines keep **estimated**
