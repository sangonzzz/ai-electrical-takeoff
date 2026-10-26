# Agente 6 — Frontend (web/)

## Estado

Home polls document sheet status only (no jobs merge); cards open on succeeded / current_run_id.

## Hecho

- Dropped `getDocumentWithJobStatuses` / `mergeJobStatuses` — document `sheets[].status` is source of truth
- Poll `GET /api/documents/{id}` every 2s while any sheet is queued/running
- `sheetIsOpenable`: succeeded, or `current_run_id` set when status is not in-flight/failed
- Cards still show A1-111 + ELECTRICAL PLAN titles; maps Agente 5 `job_id`/`status`/`error`
- Ack to Agente 5 for document sheet job fields
- Earlier: UI redesign, pnpm pin, takeoff/CRUD/review

## Cómo probarlo

```bash
cd web
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
pnpm exec vitest run
# API: VITE_USE_FIXTURE=false pnpm dev → Load demo → cards track sheets[].status → Open when succeeded
```

## Siguiente

- Lazy fixture import (Agente 1: dynamic `import()` when `VITE_USE_FIXTURE=true`)
- Optional: real sheet thumbnails from `image.png`

## Bloqueos

- Ninguno

## Decisions

- Product name in chrome: **Atreyus**
- Do not merge `/api/jobs` into the document cache; Agente 5 embeds status on each sheet
- Openable = succeeded OR (current_run_id set and not queued/running/failed)

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

El reviewer y Agente 5 confirmaron la causa: el GET del documento no traía `job_id`/`status`
por hoja, y al refetch se perdían. Agente 5 ya los agrega. Cambié el home para que solo
pollée el documento cada 2 s y lea `sheets[].status` — sin llamar a `/jobs` ni mergear
cache. La card se puede abrir cuando está `succeeded` o cuando hay `current_run_id` (si
no sigue en cola/corriendo). Títulos A1-111 siguen viniendo del mismo GET.
