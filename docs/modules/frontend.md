# Module: frontend (`web/`)

Owner: Agente 6.

## What it does

React app for reviewing and correcting electrical takeoffs on the plan. Reviewers
pan/zoom an SVG overlay whose `viewBox` is the electrical viewport in PDF points,
so marks, rooms, wires and boxes share the engine coordinate space with no manual
conversion. Counts come from a TypeScript mirror of `compute_takeoff`; clicking a
table cell highlights exactly the marks that make that number.

## Stack

React 19 + TypeScript + Vite, pnpm, TanStack Query, Zustand, react-zoom-pan-pinch,
Tailwind CSS v4, lucide-react, Vitest + Testing Library.

## Modes

| Mode | How | Behavior |
|------|-----|----------|
| Fixture | `VITE_USE_FIXTURE=true` | Loads `contracts/fixtures/sheet_result.sample.json`. CRUD + undo run in memory. Plan image is a placeholder grid until the backend serves `image.png`. |
| Live API | `VITE_USE_FIXTURE=false` | Talks to FastAPI (`VITE_API_BASE_URL`, default proxied `/api` → `:8000`). |

## Screens

1. **Home** — upload PDF or "Load demo plans"; 4 sheet cards; job status polled every 2 s.
2. **Sheet view** — plan + overlay, toolbar (select / add / undo), right panel tabs:
   Takeoff, Details, BOM, Corrections log.

## Overlay layers (SPEC palette)

| Layer | Visual |
|-------|--------|
| Rooms | Translucent polygons + dark display names |
| Detections | Category color + letter; dashed orange ring if `needs_review` |
| Wires | Magenta dashed polyline + `"14/2 - 12.4 ft"` |
| Boxes | Dark dashed rect + `"2G"` |

Colors (must match `overlay.py`): ceiling_fan `#7C3AED`, light `#F59E0B`,
switch `#2563EB`, receptacle `#059669`, exhaust_fan `#0891B2`, detector `#DC2626`,
junction_box `#6B7280`, wires `#DB2777`, boxes `#111827`, needs_review `#EA580C`.

## Counting

`web/src/lib/takeoff.ts` mirrors `engine/takeoff_engine/takeoff.py`:

- Skip `status == "deleted"`.
- Bump both `category` and `category.subtype`.
- Unknown / missing `room_id` → `unassigned` (still in totals).

Tested against `contracts/fixtures/takeoff.sample.expected.json`.

## CRUD

- Select click → Details (type, subtype, codes, room, confidence, source, evidence).
- Drag moves center (local cache each frame; PATCH on mouseup).
- Add mode: choose category/subtype, click plan.
- Delete button or Delete/Backspace; Undo (fixture stack / Ctrl+Z).
- Mutations are optimistic with rollback on error; takeoff recomputes from the
  detection list in cache so counts update instantly.

## Key files

```
web/src/
  api/client.ts          fixture vs live API switch
  api/fixture.ts         in-memory demo state + undo
  lib/takeoff.ts         computeTakeoff + detectionIdsForCount
  lib/colors.ts          SPEC palette
  store/uiStore.ts       mode, layers, selection, highlight
  components/PlanOverlay.tsx   SVG viewBox = viewport
  pages/HomePage.tsx, SheetPage.tsx
```

## How to run

```bash
cd web
pnpm install
# Fixture demo (default via .env.example):
pnpm dev
# Tests / CI:
pnpm exec tsc --noEmit
pnpm exec vitest run
pnpm build
```

## Known limits

- Fixture BOM is a lightweight derivation of sample wires/boxes, not Agente 8 pricing.
- Live undo waits on a backend endpoint; fixture mode has a local stack.
- Sheet cards 2–4 in fixture mode reuse Plan 1 geometry with renamed ids.
- `web/src/types/contracts.ts` is owned by Agente 1 (do not hand-edit).
