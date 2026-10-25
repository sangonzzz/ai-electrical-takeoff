# Agente 6 — Frontend (web/)

## Estado

M1–M3 listos en fixture mode; M4 cableado contra API (esperando endpoints de Agente 5).

## Hecho

- Scaffold Vite + React + TS + Tailwind v4 + TanStack Query + Zustand + zoom-pan-pinch + Vitest
- Fixture mode (`VITE_USE_FIXTURE=true`): carga `sheet_result.sample.json`, overlay SVG con `viewBox` = viewport PDF
- Capas: rooms, detections (palette SPEC + letra), wires (`14/2 - N ft`), boxes (`2G`), needs_review, legend, pan/zoom
- Takeoff panel: `web/src/lib/takeoff.ts` espejo de `compute_takeoff`; click celda → highlight; tests vs fixture expected
- CRUD: select, drag, add, edit type/room, delete + Del, undo; optimistic + rollback
- Home: upload + Load demo plans + 4 sheet cards + polling 2 s (listo para backend)
- Docs: `docs/modules/frontend.md`

## Cómo probarlo

```bash
cd web
pnpm install
pnpm dev
# browser → http://localhost:5173 → "Load demo plans" → Open Plan 1
pnpm exec tsc --noEmit
pnpm exec vitest run
pnpm build
```

## Siguiente

- Conectar M4 a endpoints reales cuando Agente 5 anuncie /docs
- Sustituir placeholder grid por `GET /api/sheets/{id}/image.png`
- BOM real de Agente 8 vía API (hoy hay BOM demo en fixture)

## Bloqueos

- Endpoints + contrato de respuestas de Agente 5 (FakeEngine OK)
- Imagen del plan desde backend

## Decisions

- En fixture, sheets 2–4 reusan geometría de Plan 1 con ids renombrados (demo de 4 cards)
- BOM en fixture se deriva de wires/boxes del sample (no precios de `price_list.yaml`)
- Drag: actualiza cache en cada frame; PATCH solo en mouseup
- Undo local solo en fixture hasta que exista endpoint de undo

## Needs from Santiago

- (ninguno por ahora; clave Anthropic no aplica al frontend)

## Explicación para Santiago

El frontend ya se puede demear sin backend: activás fixture mode, cargás los planes demo y ves el plano con cuartos, marcas de color, cables y cajas. La tabla de takeoff a la derecha cuenta igual que el motor en Python; si tocás un número, se iluminan exactamente esas marcas en el dibujo (eso es el momento clave de la demo). Podés agregar, mover, cambiar tipo/cuarto y borrar, y los totales cambian al toque. Cuando Agente 5 tenga la API, apagamos fixture y usamos upload + imagen real + BOM del servidor.
