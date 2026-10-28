# Module: frontend (`web/`)

Owner: Agente 6.

## What it does

React app for reviewing and correcting electrical takeoffs on the plan. Product
name in the UI: **Electrical Takeoff**. Visual direction: precision blueprint
review — slate chrome, bright plan sheet on a dark canvas, SPEC category colors
only on marks. Counts come from a TypeScript mirror of `compute_takeoff`.

## Stack

React 19 + TypeScript + Vite, pnpm (`packageManager: pnpm@10.28.0`), TanStack Query,
Zustand, react-zoom-pan-pinch, Tailwind CSS v4, lucide-react, Vitest.

Typography: **Inter** (UI) + **JetBrains Mono** (numbers). Spacing base 8 px,
radius 10 px, transitions ~150 ms. Light theme default.

## Screens

1. **Home** — hero, “Load demo plans”, upload, sheet cards with `sheet_number` /
   `title` and job status from `GET /api/documents/{id}` (poll every 2 s while
   queued/running).
2. **Sheet** — header (plan tabs, pipeline + short `file_hash`, Undo/Redo,
   review/export, **Re-run fresh analysis**), KPI strip, component palette,
   plan canvas, right panel.

## Editing

- **Undo / Redo** — labeled header buttons; Ctrl+Z / Ctrl+Shift+Z.
  Fixture: snapshot stacks. Real API: client command stack
  (create↔delete/restore, update/move↔PATCH previous values; wire create/delete/restore
  and wire PATCH previous values); clears redo on new action; refreshes sheet/BOM/corrections.
- **Component palette** — drag subtypes onto the plan (ghost + “Drop on the plan”);
  click-to-add still works in Add mode. Room auto-assigned on create.
- **Details** — editable X/Y in PDF points (also drag marks on the plan).
- **Edit cables** (header + toolbar toggle, off by default) — turns Wires layer on; runs
  colored by type (`nm_14_2` pink, `nm_14_3` green `#16A34A`); hover label keeps type +
  length. Selected run shows round handles (`data-testid="wire-handle"`): drag vertex to
  reshape, double-click run to add a bend, Alt+click vertex to remove, drag an end onto a
  device to reconnect (PATCH points + from/to). Delete key removes the selected run.
  Details panel: type, from/to, lengths, source, delete. Undo/redo covers reshape/reconnect.
  Wires layer on → hint “Select a cable to edit, or New cable to add one”.
- **New cable** — click device A then B; dashed preview follows cursor; Esc cancels;
  straight run via `POST .../wire-runs` (fixture mock until Agente 5 ships).
- **Move device** — drag updates attached run tips live; commit on drop returns
  `wire_runs` / `boxes` / `bom`; BOM panel shows total + delta badge vs open baseline.
- **Boxes** — layer shows `1G`/`2G`/`3G` marks (`data-testid="box-mark"`); click opens
  derived box details and highlights member devices (no direct box edit).
- Detection marks expose `data-testid="detection-mark"`; wires `wire-run`,
  `wire-run-type-select`, `wire-run-delete`, `wire-create-mode` for e2e.

## Plan canvas

- SVG `viewBox` = electrical viewport (PDF points).
- Marks: filled circle + letter; selected pulse; highlight dims others.
- Rooms: subtle dashed outlines; open-plan shared edges as thinner “auto boundary”
  dashes with hover label (detected client-side from shared polygon edges).
- Wires: **off by default**, beta badge + tooltip about dashed-line tracing limits;
  when on, labels only on hover or when wire count ≤ 14 (always on hover in Edit cables).
- Boxes off by default. Floating toolbar: select / add / fit / **Edit cables** / layers.
- BOM: prominent total at top; cable section “Cable (estimated)”; Assumptions
  collapsed by default with human labels (hides dash/gap medians — Excel only).
- **Re-run fresh analysis** → confirm → `POST /api/sheets/{id}/reanalyze`, poll job, reload.

## Keyboard

| Key | Action |
|-----|--------|
| V | Select |
| A | Add |
| F | Fit |
| Del | Delete selected mark or cable |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| Esc | Clear / exit add or New cable |
| ? | Cheat sheet |

## Exports / review API

- `POST /api/sheets/{id}/review-complete`
- `GET /api/sheets/{id}/ground-truth.json`
- `GET /api/sheets/{id}/export.xlsx` — Download Excel
- `GET /api/sheets/{id}/quote.pdf` — Download quote PDF

## How to run

```bash
cd web
corepack enable
pnpm install --frozen-lockfile
pnpm dev
# Fixture: VITE_USE_FIXTURE=true
pnpm exec tsc --noEmit && pnpm exec vitest run
```

## Known limits

- Fixture BOM is a lightweight derivation of sample wires/boxes.
- Fixture undo uses full-result snapshots; API mode uses per-action inverses +
  `POST /api/detections/{id}/restore` (Agente 5).
- `web/src/types/contracts.ts` is owned by Agente 1.
- Lazy fixture JSON import (Agente 1 request) still pending.
