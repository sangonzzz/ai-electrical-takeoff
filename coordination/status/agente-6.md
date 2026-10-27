# Agente 6 — Frontend (web/)

## Estado

Wires layer off by default (beta + tooltip); BOM cable lines marked estimated.

## Hecho

- Wires layer default **off**; small **beta** badge; tooltip on dashed-line tracing limits
- BOM: section “Cable (estimated)” + per-line `estimated` badge
- Earlier: client Undo/Redo stack, palette DnD, X/Y, Excel/quote, Electrical Takeoff rename

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit
pnpm dev
# Sheet: Wires toggle shows beta; hover for tooltip; BOM cable rows say estimated
```

## Siguiente

- Lazy fixture import (Agente 1)

## Bloqueos

- Ninguno

## Decisions

- Wires off by default so reviewers don’t quote unreviewed cable traces
- Product display name: Electrical Takeoff

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

La capa de cables arranca apagada, con un badge “beta” y un tooltip que explica que
se trazan desde las líneas punteadas y que a veces agarran millwork/gabinetes — hay
que revisar antes de cotizar. En el BOM las líneas de cable dicen “estimated”.
