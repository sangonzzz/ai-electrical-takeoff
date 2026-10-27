# Agente 6 — Frontend (web/)

## Estado

Room auto-boundaries styled intentionally; Re-run fresh analysis with confirm + reload.

## Hecho

- Rooms layer: subtle dashed outlines; shared open-plan edges as thin “auto boundary” (hover label)
- `POST /api/sheets/{id}/reanalyze` via header action + confirmation; polls job; invalidates sheet/BOM
- Earlier: wires beta off, BOM estimated, client Undo/Redo, palette DnD, Excel/quote

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run
pnpm dev
# Toggle Rooms: dashed outlines; hover shared Living/Kitchen edge → "auto boundary"
# Header → Re-run fresh analysis → confirm → waits for job → sheet reloads
```

## Siguiente

- Lazy fixture import (Agente 1)

## Bloqueos

- Ninguno

## Decisions

- Auto boundaries detected client-side (shared polygon edges within 2.5 pt), no schema change
- Reanalyze polls up to 5 minutes then errors with a reload hint

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Los límites de habitación ahora se ven como líneas punteadas suaves. Cuando el motor
parte un open-plan (Living/Kitchen) sin pared real, esa línea se dibuja más fina y al
pasar el mouse dice “auto boundary”, para que no parezca un trazo suelto. También hay
un botón “Re-run fresh analysis” con confirmación que llama al reanalyze de la API y
recarga la hoja cuando el job termina.
