# Agente 6 — Frontend (web/)

## Estado

Demo polish shipped: takeoff headers/subtypes, category filter, fit-to-screen, review/export wired to A5.

## Hecho

- Takeoff table: named columns + icons (Fans, Lights, …); room row expands subtype breakdown
- `needs_review` ring only when `needs_review === true`
- Boxes layer **off** by default; multi-gang (2G+) emphasized when on
- Room name overlays hidden by default; show on polygon hover + in Details
- Fit-to-screen on load/resize + Fit button; category filter to solo one type
- Review workflow: Mark sheet reviewed (`POST …/review-complete`), Export ground truth (`GET …/ground-truth.json`)
- `getSheet` normalizes Agente 5 `SheetDetailResponse` (incl. `human_reviewed`)

## Cómo probarlo

```bash
cd web
pnpm install
# Against real backend (reviewer path):
# VITE_USE_FIXTURE=false in web/.env
pnpm dev
# http://localhost:5173 → Load demo → open a sheet
# Click room name in takeoff → expand subtypes; toggle category filter; Fit;
# Mark sheet reviewed; Export ground truth
pnpm exec tsc --noEmit
pnpm exec vitest run
```

## Siguiente

- Optional: wire undo to a backend endpoint if A5 adds one
- Keep palette in sync with A7 overlay

## Bloqueos

- Ninguno para la demo actual

## Decisions

- Boxes default off; 1-gang faint when boxes layer on
- Room labels hover-only (plan raster already has text)
- Category filter is independent of layer toggles
- Ground-truth download uses browser blob + Content-Disposition filename

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Pulí la pantalla de demo con lo que pediste en la review: la tabla ahora dice Fans/Lights/… con íconos, y al hacer click en un cuarto se abren los subtipos (por ejemplo Switches 3: dimmer, fan…). El anillo naranja de “needs review” solo aparece si el flag es true. Las cajas arrancan apagadas; si las prendés, los 2G/3G se ven fuertes. Los nombres de cuarto no tapan el plano (hover o panel Details). El plano hace fit al cargar, hay filtro por categoría para revisar de a un tipo, y los botones “Mark sheet reviewed” / “Export ground truth” hablan con los endpoints nuevos de Agente 5.
