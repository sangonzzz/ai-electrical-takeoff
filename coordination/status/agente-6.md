# Agente 6 — Frontend (web/)

## Estado

Tres fixes UI para demo: BOM card, decimales locale-proof, handles RDP. Listo para v1.0.3.

## Hecho

- BOM summary card: label “Estimated material cost”, amount sans `$2,254.09` (`bom-total`), footnote HD; e2e `getByTestId("bom-total")`
- Plan length / Vertical / X / Y: `type="text" inputMode="decimal"`, parse `,` o `.`, display con punto
- Handles en runs densos (>12 pts): RDP ≤12; trazo completo hasta el primer edit
- Commits: `9092991`, `1306b87`, `40eafaf`

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm build
```

## Siguiente

- Agente 1 tag v1.0.3 (reviewer corre cable e2e)

## Bloqueos

- Ninguno

## Decisions

- Subtotales en card solo si suman al total ±$0.01
- No inventar fecha de precios si el BOM no la trae

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

El BOM ahora muestra una tarjeta clara con el costo estimado (número grande, sin mono).
Los campos de largo y X/Y ya no se confunden en español (punto siempre). En cables
muy densos solo ves hasta 12 bolitas de edición; el trazo se ve completo hasta que
muevas un handle. Tres commits locales; no hice push.
