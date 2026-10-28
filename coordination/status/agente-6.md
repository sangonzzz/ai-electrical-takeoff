# Agente 6 — Frontend (web/)

## Estado

BOM total vuelve a coincidir con el selector e2e `/Total\s*\$/` (desbloqueo v1.0.2).

## Hecho

- `<p data-testid="bom-total">Total {formatUsd(...)}</p>` — un solo match de `/Total\s*\$/`
- Vitest en `BomPanel.test.tsx` fija el contrato
- Assumptions colapsables + labels humanos (cambio anterior)
- Cables coloreados / handles / Edit cables en header

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm build
```

## Siguiente

- Agente 1 re-corre release UI v1.0.2

## Bloqueos

- Ninguno

## Decisions

- `formatUsd` con `en-US` (comas) — e2e ya parsea `[\d,.]+`

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

El total del BOM otra vez dice “Total $…” en un solo elemento, como pide el e2e.
Así Agente 1 puede sacar v1.0.2 sin tocar el engine. Typecheck, Vitest y build OK.
