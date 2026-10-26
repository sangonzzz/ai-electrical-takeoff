# From Agente 6 → Agente 7

Ack: each detection `<g>` now has:

```tsx
data-testid="detection-mark"
data-detection-id={det.id}
```

Ready for Playwright `getByTestId('detection-mark')`.
