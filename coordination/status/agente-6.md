# Agente 6 — Frontend (web/)

## Estado

Cables coloreados por tipo + handles de reshape/reconnect; Edit cables también en el header.

## Hecho

- Colores: `nm_14_2` rosa `#DB2777`, `nm_14_3` verde `#16A34A`; leyenda 14/2 y 14/3
- Edit cables: handles redondos en extremos y vértices (`data-testid="wire-handle"`)
  - Drag vértice → reshape; doble clic en run → agrega vértice; Alt+clic → quita
  - Drag extremo sobre un dispositivo → reconnect (snap) + PATCH points/from/to
  - Delete borra el run seleccionado; undo/redo vía command stack / fixture
- Discoverability: botón **Edit cables** en header junto a Undo/Redo; hint al prender Wires
- BOM: sección **Fixtures (allowance)** (pedido Agente 8)
- Mensaje a Agente 7 con pasos e2e de reshape/reconnect

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm run build
pnpm dev   # VITE_USE_FIXTURE=true
# Header o toolbar → Edit cables → seleccionar run rosa/verde → drag handles
# Doble clic en el trazo → nuevo vértice; Alt+clic en handle → quitar
# Arrastrar extremo hasta otro mark → reconnect; ver Details length + BOM
# Del → borra run; Ctrl+Z deshace
```

## Siguiente

- (ninguno bloqueante) Agente 7 e2e de handles

## Bloqueos

- Ninguno

## Decisions

- Seleccionar un cable con la capa Wires on enciende Edit cables (discoverability)
- Alt+clic en un extremo con >2 puntos lo quita y limpia from/to de ese extremo
- Snap de reconnect: 22 pt PDF

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Los cables ya no son todos rosa: el 14/2 sigue rosa y el 14/3 es verde, como en la leyenda.
Hay un botón **Edit cables** arriba junto a Undo, además del de la barra flotante. Con
edición activa, el cable seleccionado muestra bolitas en cada esquina: las arrastrás para
cambiar la forma, doble clic agrega un codo, Alt+clic lo saca, y si soltás un extremo
encima de otro dispositivo, el cable se reconecta. Todo eso manda un PATCH al API (o al
mock en fixture) y el BOM se actualiza; Undo/Redo lo deshace. Si solo prendés la capa
Wires, aparece un tip de una línea para que sepas que podés editar o crear un cable.
