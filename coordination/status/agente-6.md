# Agente 6 — Frontend (web/)

## Estado

Review/Steven polish shipped: Undo/Redo, palette drag-drop, X/Y fields, wire label density, Excel/quote export, renamed to Electrical Takeoff.

## Hecho

- Product rename: **Electrical Takeoff** (no Atreyus in UI)
- Undo + Redo labeled in top bar (Ctrl+Z / Ctrl+Shift+Z); clear disabled state; fixture redo stack
- Component palette with icons; drag ghost + “Drop on the plan”; click-to-add kept; room auto-assign
- Details: editable X/Y PDF points
- Wire labels only on hover (or all when ≤14 wires)
- Download Excel (`export.xlsx`) + Download quote PDF (`quote.pdf`); short `file_hash` in header
- `data-testid="detection-mark"` for Agente 7 e2e
- Earlier: home job poll from document status, UI redesign

## Cómo probarlo

```bash
cd web
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
pnpm exec vitest run
VITE_USE_FIXTURE=true pnpm dev
# Sheet: Undo/Redo after edit; drag a receptacle onto the plan; edit X/Y; hover wires on plan 2;
# Download Excel / quote PDF buttons in the header
```

## Siguiente

- Lazy fixture import (Agente 1)
- Smoke-test Excel/quote against live Agente 5 routes when ready

## Bloqueos

- Excel/quote PDF API routes still landing (UI wired; fixture stubs downloads)

## Decisions

- Product display name: **Electrical Takeoff**
- Wire label low-density threshold: 14 runs
- Undo/Redo live in the header (not only the floating toolbar)

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Agregué lo que pidió la review y Steven: botones Undo/Redo visibles arriba con atajos,
una paleta de componentes para arrastrar marcas al plano (con fantasma y “Drop on the plan”),
campos X/Y editables en Details, labels de cables solo al hover cuando hay muchos,
exports Excel y PDF de cotización, y el nombre del producto ahora es Electrical Takeoff
(sin Atreyus). Commits chicos por feature.
