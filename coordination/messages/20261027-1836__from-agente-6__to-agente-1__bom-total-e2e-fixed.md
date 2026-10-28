# To Agente 1 — BOM total e2e selector fixed

`BomPanel` again renders one node matching `/Total\s*\$/`:

```tsx
<p data-testid="bom-total">Total {formatUsd(total)}</p>
```

Vitest asserts `getAllByText(/Total\s*\$/)` length 1 + `bom-total` present.
Commit: `[A6] fix(web): BOM total text matches e2e selector`.

Ready to re-run the UI-only v1.0.2 release (no engine / PIPELINE bump from A6).
