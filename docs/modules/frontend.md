# Module: frontend (`web/`)

Owner: Agente 6.

## What it does

React app for reviewing and correcting electrical takeoffs on the plan. Visual
direction: **precision blueprint review** — slate chrome, bright plan sheet on a
dark canvas, SPEC category colors only on marks. Counts come from a TypeScript
mirror of `compute_takeoff`; clicking a KPI or takeoff cell highlights those marks.

## Stack

React 19 + TypeScript + Vite, pnpm (`packageManager: pnpm@10.28.0`), TanStack Query,
Zustand, react-zoom-pan-pinch, Tailwind CSS v4, lucide-react, Vitest.

Typography: **Inter** (UI) + **JetBrains Mono** (numbers). Spacing base 8 px,
radius 10 px, transitions ~150 ms. Light theme default.

## Screens

1. **Home** — hero, primary “Load demo plans”, upload, 4 sheet cards (thumbnail + status).
2. **Sheet** — header (plan tabs, pipeline badge, needs-review count, review/export),
   KPI strip, dark-canvas plan with floating toolbar + mini legend, right panel tabs.

## Plan canvas

- SVG `viewBox` = electrical viewport (PDF points).
- Marks: filled circle + letter, white outline, drop shadow; hover `<title>` tooltip;
  selected = pulsing ring; highlight dims everything else.
- Rooms: polygons; names on hover only.
- Wires: pink curves + label pill `14/2 - 12.4 ft`.
- Boxes: off by default; multi-gang labeled squares.
- Floating toolbar: select / add / undo / fit / layers. Mini legend bottom-left.
- Category filter (solo one type at a time).

## Keyboard

| Key | Action |
|-----|--------|
| V | Select |
| A | Add |
| F | Fit |
| Del | Delete selected |
| Ctrl+Z | Undo |
| Esc | Clear / exit add |
| ? | Cheat sheet |

## Review API

- `POST /api/sheets/{id}/review-complete`
- `GET /api/sheets/{id}/ground-truth.json`

## How to run

```bash
cd web
corepack enable
pnpm install --frozen-lockfile
pnpm dev
# Fixture: VITE_USE_FIXTURE=true
pnpm exec tsc --noEmit && pnpm exec vitest run
```

Screenshots (local, gitignored under `out/debug/`): `ui-home.png`, `ui-sheet.png`.

## Known limits

- Fixture BOM is a lightweight derivation of sample wires/boxes.
- Live undo awaits a backend endpoint; fixture has a local stack.
- `web/src/types/contracts.ts` is owned by Agente 1.
