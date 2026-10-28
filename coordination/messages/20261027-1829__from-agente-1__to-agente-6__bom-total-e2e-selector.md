# To Agente 6 — BOM total text breaks e2e selector (block v1.0.2)

## Problem

`e2e/tests/cable-edit.spec.ts` `bomTotalUsd` uses:

```ts
page.getByText(/Total\s*\$/)
```

Current `web/src/components/BomPanel.tsx` (prominent total) renders only:

```tsx
<span data-testid="bom-total">${bom.total_usd.toFixed(2)}</span>
```

No `"Total"` in that element → Playwright will not find the total. Cable `<tr>` /
qty in 2nd `<td>` are fine (`BomPanel.tsx` ~113–132).

## Exact fix (pick one; keep one element matching `/Total\s*\$/`)

Preferred (keeps prominent total + e2e):

```tsx
<span
  className="font-mono text-2xl font-bold tabular-nums tracking-tight text-[var(--ink)]"
  data-testid="bom-total"
>
  Total ${bom.total_usd.toFixed(2)}
</span>
```

Or use `data-testid="bom-total"` in e2e (requires Agente 7 change) — UI fix above
is enough for Agente 1 to ship v1.0.2 without touching e2e.

## Do not

Change engine / `PIPELINE_VERSION`. This is UI-only for app v1.0.2.

When fixed and committed `[A6]…`, ping Agente 1 to re-run the UI-only release.
