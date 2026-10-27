# Agente 6 — Frontend (web/)

## Estado

Edit cables en el plan (toggle + create/select/delete + boxes + BOM delta); listo en fixture.

## Hecho

- Toggle **Edit cables** (off by default) → enciende Wires, selección de runs, hit area ancha, hover `14/2 - 12.4 ft`
- Panel Details para cable: tipo 14/2|14/3, from/to (highlight), longitudes, source, delete
- **New cable**: A→B con preview dashed; Esc cancela
- Drag de dispositivo actualiza tips de runs en vivo; drop → PATCH detection (wires/boxes/bom)
- Capa Boxes: marcas 1G/2G/3G; click → details + highlight devices (derivadas)
- Undo/redo: wire create/delete/restore + wire PATCH previous; detection moves unchanged
- BOM: badge delta (ej. `+$3.12`) vs total al abrir; cable sigue con label **estimated**
- Fixture mock: CRUD wire + restore; PATCH detection returns wire_runs/boxes/bom
- `data-testid`: `wire-run`, `wire-run-type-select`, `wire-run-delete`, `wire-create-mode`, `box-mark`
- Wires layer sigue con badge **beta**

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm run build
pnpm dev   # VITE_USE_FIXTURE=true
# Abrir sheet → Edit cables → hover/select pink run → cambiar tipo → ver BOM
# New cable → click device A → B → Esc cancela mid-flight
# Drag un switch → runs se mueven → soltar → Boxes/BOM
# Boxes layer → click 2G → devices highlighted
# Ctrl+Z / Ctrl+Shift+Z after wire edits
```

## Siguiente

- Cuando Agente 5 mergee wire-runs HTTP, quitar dependencia del mock (client ya apunta a las mismas rutas)
- Screenshots de Edit cables si Santiago quiere assets en `out/debug/`

## Bloqueos

- Ninguno funcional en fixture. API real de Agente 5 está en progreso en el mismo repo (no tocada por A6).

## Decisions

- Edit cables apagado por defecto; al activarlo fuerza `layers.wires = true` (no apaga al desactivar)
- Create body siempre manda points + cable_type + lengths (compatible con schema A5 opcional)
- Delta BOM = total actual − total al primer load del BomPanel (baseline en uiStore)
- Highlight from/to y boxes usa `highlightDevices` sin salir del tab Details

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Hay un interruptor nuevo en la barra flotante: **Edit cables**. Por defecto está apagado,
así que el flujo de marcas / palette / undo que ya usabas no cambia. Cuando lo enciendes,
aparece la capa de cables y puedes hacer clic en un trazo rosa para ver el panel de
detalles (tipo 14/2 o 14/3, de–a, longitudes, borrar). **New cable** te deja elegir dos
dispositivos; una línea punteada sigue el mouse entre medias. Si arrastras un switch,
los cables pegados se mueven en vivo y al soltar se recalculan cajas y el BOM (con un
badge del cambio de precio). Las cajas solo se miran (1G/2G/3G); no se editan a mano.
Undo/Redo también deshace altas/bajas/cambios de cable. Todo está mockeado en fixture
hasta que el backend de Agente 5 quede estable; las rutas del cliente ya coinciden.
