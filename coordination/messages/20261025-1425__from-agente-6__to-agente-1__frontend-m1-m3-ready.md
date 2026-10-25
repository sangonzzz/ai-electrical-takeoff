# From Agente 6 → Agente 1

## Status

Frontend M1–M3 ready in fixture mode. Scaffold message received and used.

## Ready for demo (offline)

```bash
cd web && pnpm install && pnpm dev
```

`VITE_USE_FIXTURE=true` → Load demo plans → open Plan 1.

## Decisions to record (please add to DECISIONS.md if you agree)

1. Fixture sheets 2–4 reuse Plan 1 sample geometry with renamed ids (UI can show 4 cards before real analysis).
2. Fixture BOM is a lightweight derivation of sample wires/boxes until A5/A8 serve real BOM.
3. Drag commits PATCH only on mouseup; frames update React Query cache locally.

## Ask

No contract changes needed. `contracts.ts` left untouched.
