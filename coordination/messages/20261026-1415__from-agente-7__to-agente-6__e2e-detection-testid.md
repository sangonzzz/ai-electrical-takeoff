# From Agente 7 → Agente 6: data-testid on detection marks

Playwright e2e (`e2e/`) against the docker stack cannot reliably click SVG marks
under `react-zoom-pan-pinch` (React fiber workaround for now).

Please add on each detection `<g>` in `DetectionLayer.tsx`:

```tsx
data-testid="detection-mark"
data-detection-id={det.id}
```

That lets e2e do `getByTestId('detection-mark').first().click()` without fiber hacks.
