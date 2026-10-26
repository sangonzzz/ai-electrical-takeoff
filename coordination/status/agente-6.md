# Agente 6 — Frontend (web/)

## Estado

Home job-status poll fixed (no more Running→Queued forever); cards show real sheet_number/title.

## Hecho

- Job poll: `getDocumentWithJobStatuses` refetches document + jobs; stop only on succeeded/failed
- Status mapping in `lib/jobs.ts` (completed/success/… → succeeded; running aliases; etc.)
- Upload (`document_id`/`job_id`) and detail (`id`/`current_run_id`) both normalize to `DocumentSummary`
- Sheet cards: A1-111 + “ELECTRICAL PLAN - PLAN N” (never bare “P1”)
- UI redesign “precision blueprint review” + screenshots (`out/debug/ui-*.png`)
- pnpm pin 10.28.0, takeoff/CRUD/review wiring

## Cómo probarlo

```bash
cd web
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
pnpm exec vitest run
# API mode (jobs succeed → cards stay Succeeded with titles):
# VITE_USE_FIXTURE=false pnpm dev → Load demo → watch cards leave Queued
# Fixture: VITE_USE_FIXTURE=true pnpm dev → cards already Succeeded with A1-111…
```

## Siguiente

- Lazy fixture import (Agente 1 asked: dynamic `import()` when `VITE_USE_FIXTURE=true`)
- Optional: real sheet thumbnails from `image.png` when API available

## Bloqueos

- Ninguno para la demo

## Decisions

- Product display name in chrome: **Atreyus** (repo remains ai-electrical-takeoff)
- KPI strip omits junction_box (still in takeoff table + legend)
- Document id remembered in sessionStorage so home restores after sheet navigation
- Never overwrite React Query document cache with raw GET detail (no status field) — always merge via jobs helpers

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Había un bug en home: las cards pasaban a Running y después quedaban en Queued para
siempre aunque el worker terminaba bien. La causa era que al refetch del documento se
pisaba el cache con un payload sin `status` (y `current_run_id` en vez de `job_id`),
así que todo volvía a “queued”. Ahora un solo poll pide documento + jobs, normaliza
estados (completed → succeeded, etc.) y solo para cuando todos terminaron. Al terminar
también llegan `sheet_number` y `title` reales (A1-111, ELECTRICAL PLAN - PLAN N).
Tests de `lib/jobs` verdes; tsc + vitest OK.
