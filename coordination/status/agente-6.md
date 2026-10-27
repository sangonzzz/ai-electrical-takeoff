# Agente 6 — Frontend (web/)

## Estado

Real-API Undo/Redo via client command stack + Agente 5 restore; asked Agente 7 to re-run e2e.

## Hecho

- Client command stack (`lib/commandStack.ts`): create→delete, delete→restore, update/move→PATCH previous
- `restoreDetection` → `POST /api/detections/{id}/restore`
- canUndo/canRedo enable after edits in API mode; redo cleared on new action; BOM/sheet refresh
- Ctrl+Z / Ctrl+Shift+Z unchanged; fixture stacks kept
- Messages to Agente 5 (restore dependency) and Agente 7 (re-run e2e)
- Earlier: palette DnD, X/Y, wire labels, Excel/quote, Electrical Takeoff rename

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run
# Against API (Agente 5 restore live):
# VITE_USE_FIXTURE=false pnpm dev → add mark → Undo enables → count drops → Redo restores
# Agente 7: make e2e  # expect undo_then_redo pass
```

## Siguiente

- Lazy fixture import (Agente 1)
- Confirm e2e undo_then_redo after A5 commits restore

## Bloqueos

- e2e undo needs Agente 5 restore route committed/deployed in the stack under test

## Decisions

- Client-owned history for API mode (not server `/undo` tip) so Undo works for the session’s edits even before corrections-log undo lands
- Soft-delete restore preserves detection id across undo create / redo create

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Antes Undo/Redo solo andaban en fixture. Ahora en API real cada acción guarda su
inversa: crear se deshace con delete, borrar con restore, mover/editar con un PATCH
de los valores anteriores. Redo vuelve a aplicar; si hacés algo nuevo se limpia el
redo. Los botones se habilitan de verdad y el takeoff/BOM se refrescan. Le pedí a
Agente 7 que vuelva a correr el e2e.
