# Agente 6 — Frontend (web/)

## Estado

UI redesign “precision blueprint review” shipped for the interview demo; screenshots checked.

## Hecho

- Visual system: slate chrome, dark canvas + bright sheet, Inter + JetBrains Mono, 8px / 10px / 150ms
- Home: hero, Load demo primary, 4 sheet cards with thumbnails + status, empty/loading states
- Sheet header: plan tabs 1–4, pipeline badge, needs-review count, review/export, shortcuts
- KPI strip (Fans…Detectors) clickable → highlight marks
- Plan canvas: crisp marks + tooltip, pulse select, highlight dim, wire pills, floating toolbar, mini legend
- Right panel: zebra takeoff + expandable subtypes, details (confidence bar, code chips), BOM sections, log timeline
- Keyboard: V/A/F/Del/Ctrl+Z/? cheat sheet
- Screenshots: `out/debug/ui-home.png`, `out/debug/ui-sheet.png` (verified in browser)
- Earlier: pnpm pin 10.28.0, takeoff/CRUD/review wiring

## Cómo probarlo

```bash
cd web
pnpm install --frozen-lockfile
pnpm dev
# http://localhost:5173 → Load demo plans → Open Plan 1
# Check KPI click, takeoff expand, hover marks, ? shortcuts
pnpm exec tsc --noEmit
pnpm exec vitest run
```

## Siguiente

- Optional: real sheet thumbnails from `image.png` when API available
- Compose `--frozen-lockfile` (asked Agente 1)

## Bloqueos

- Ninguno para la demo

## Decisions

- Product display name in chrome: **Atreyus** (repo remains ai-electrical-takeoff)
- KPI strip omits junction_box (still in takeoff table + legend)
- Document id remembered in sessionStorage so home restores after sheet navigation

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Rediseñé la UI para la demo de entrevista: se ve como un producto de review de planos,
no como un dashboard genérico. El plano va en una hoja clara sobre un fondo oscuro; los
colores de categoría solo están en las marcas. Arriba tenés tabs Plan 1–4, el badge de
versión y cuántos necesitan review; una franja de KPIs muestra los totales y al clickear
ilumina esas marcas. A la derecha sigue el takeoff expandible, details con barra de
confianza, BOM y el log. Atajos de teclado con “?”. Saqué capturas de home y sheet y
las miré antes de cerrar.
