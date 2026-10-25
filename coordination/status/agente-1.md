# Agente 1 — Lead / architecture / integration

## Estado

Integration pass 1: deps + eval CLI + docs verdes; E2E Docker bloqueado (daemon apagado); fixture UI OK.

## Hecho

- Inbox A2–A8: DECISIONS.md actualizado (rooms, LLM Sonnet tool_choice, BOM, frontend, backend, eval)
- SPEC §1: CL Plan 3 = x4, Plan 4 = x2
- Backend deps: `sqlalchemy[asyncio]` + `greenlet`; `.env.example` ENGINE/INLINE_JOBS
- `takeoff eval` cableado; pytest pythonpath; eval/reports gitignore; CI regression step
- Makefile `demo` → `backend/scripts/demo_upload.py`; compose alembic + PYTHONPATH + ENGINE=fake
- README.md + docs/architecture.md (Mermaid)
- Mensajes a A5, A6, A7, to-all
- Tests: **82 passed, 8 skipped**; web vitest 5 + build OK; fixture UI: 4 sheets, marks, click total, BOM $20.65

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest
cd web && pnpm exec vitest run && pnpm build
# Fixture UI:
cd web && set VITE_USE_FIXTURE=true&& pnpm dev
# Full stack (requires Docker Desktop running):
docker compose up -d && make demo
```

## Siguiente

- Arrancar Docker Desktop → E2E upload → 4 jobs → CRUD real
- Pushear `.github/workflows/ci.yml` cuando haya scope `workflow`
- `ENGINE=real` cuando pipeline + DB estén estables

## Bloqueos

- Docker Desktop no está corriendo en esta máquina
- Token `gh` sin scope `workflow` para Actions

## Decisions

Ver `coordination/DECISIONS.md` (pass de integración).

## Needs from Santiago

1. Encender Docker Desktop y avisar para re-correr E2E.
2. `gh auth refresh -h github.com -s workflow,repo,read:org,gist` para subir CI.
3. Llenar `eval/ground_truth/planN.counts.yaml` (ver `eval/COMO_CONTAR.md`).
4. Confirmar precios BOM `verified: false` (lista en status A8).

## Explicación para Santiago

El sistema ya está armado de punta a punta en piezas: el motor detecta símbolos y cuartos en el PDF, Claude opcional interpreta la leyenda, el backend guarda trabajos por hoja, y el front muestra marcas + takeoff + BOM. En esta pasada de integración cableé dependencias del backend, el comando `takeoff eval`, el demo del Makefile y la documentación (README + diagramas). Los tests de Python y el build del front pasan. No pude levantar Docker (el motor de Desktop está apagado), así que el recorrido completo upload→4 jobs lo dejé pendiente; sí verifiqué el modo fixture del front: cargás demo, ves las 4 hojas, abrís Plan 1 con marcas de colores, tocás un total y se resaltan, y el BOM muestra un precio. Cuando enciendas Docker, re-corro el stack real.
