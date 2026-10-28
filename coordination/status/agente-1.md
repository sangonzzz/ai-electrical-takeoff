# Agente 1 — Lead / architecture / integration

## Estado

**v1.0.2 blocked** — BOM total text no longer matches e2e `/Total\s*\$/`.

## Hecho

- Inbox / A6 commit `243b114` present; scope web+coordination+docs only; PIPELINE 0.6.7
- Web: tsc + vitest 30 + build **OK**
- E2E selector check: (a) **NO** total; (b) **YES** cable `<tr>` qty 2nd `td`
- Message to Agente 6 with exact fix; **no** tag v1.0.2

## Cómo probarlo

```bash
# After A6 fix:
# span bom-total must contain text matching /Total\s*\$/
```

## Siguiente

- Agente 6 restores `Total $…` in one element → re-run UI-only v1.0.2

## Bloqueos

- BomPanel total missing word `Total` vs `cable-edit.spec.ts` `bomTotalUsd`

## Decisions

UI-only release requires e2e selector compatibility without running the suite.

## Needs from Santiago

- (ninguno) — waiting on Agente 6

## Explicación para Santiago

Quise sacar v1.0.2 (tarjeta Assumptions del BOM) sin pytest/e2e. El build web
pasó, pero el total ya no dice “Total $…” en un solo elemento y el e2e lo busca
así. No etiqueté. Pedí a Agente 6 que ponga `Total $…` otra vez en el span del total.
