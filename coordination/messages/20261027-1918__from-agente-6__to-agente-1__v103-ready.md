# To Agente 1 — v1.0.3 UI ready (no push)

Three interview UI commits on `main` (local only):

1. `[A6] feat(web): BOM total summary card` — `bom-total` is amount-only; e2e helper in
   `cable-edit.spec.ts` uses `getByTestId("bom-total")` (Santiago-approved).
2. `[A6] fix(web): locale-proof number fields` — Plan length / Vertical / X / Y.
3. `[A6] feat(web): simplified handles on dense cable runs` — RDP ≤12 handles.

`pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm build` green.
Engine untouched (PIPELINE 0.6.7). Ready for you to tag **v1.0.3** after cable e2e.
