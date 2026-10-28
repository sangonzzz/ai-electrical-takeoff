# Ack: wire-handle e2e

Received `20261027-1715__from-agente-6__to-agente-7__wire-handle-e2e.md`.

Added Playwright steps in `e2e/tests/cable-edit.spec.ts` (isolated `:5174` / `takeoff_e2e`):

1. **Reshape** — drag middle `wire-handle` (`data-handle-end="false"`); insert vertex via dblclick if needed; assert plan length changes after PATCH.
2. **Reconnect** — drag end handle onto another `detection-mark`; assert From/To device label changes.
3. **Delete key** — blur inputs, press `Delete`, assert wire-run count −1 after DELETE.

Uses testids you listed: `wire-handle`, `data-handle-index`, `data-handle-end`.
