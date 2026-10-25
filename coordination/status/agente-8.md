# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

M1–M4 listos: wires, boxes, assumptions/prices, compute_bom + mensajes a A5/A6.

## Hecho

- Medición real en Plan 1: dash median **7.1 pt**, gap median **3.8 pt** (doc + assumptions.yaml)
- `find_wire_runs`: encadena dashes por proximidad, snap a devices, nm_14_2 / nm_14_3, vertical allowance
- `compute_boxes`: multi-gang switches, WP cover, fan_rated, ceiling_round, none (recessed/exhaust)
- `data/assumptions.yaml` + `data/price_list.yaml` (Home Depot, verified + placeholders)
- `compute_bom` puro con `source_ids`, pies + rolls, total_usd
- Tests en `engine/tests/bom/` (16 passing)
- Debug PNGs: `out/debug/wires_plan1.png`, `boxes_plan1.png`, `boxes_fixture_schematic.png`
- Docs: `docs/modules/bom.md`
- Mensajes a Agente 5, 6 y 1

## Cómo probarlo

```bash
.venv/Scripts/python -m pytest engine/tests/bom/ -v
.venv/Scripts/python engine/tests/bom/render_debug.py
# Abrir out/debug/wires_plan1.png y boxes_fixture_schematic.png
```

## Siguiente

- Re-snappear wires cuando existan detections reales de Agente 2
- Completar precios `verified: false` cuando Santiago los pase
- Integración en pipeline (`analyze_sheet` / ENABLE_BOM) vía Agente 1–2

## Bloqueos

- Detections reales de Agente 2 (mientras tanto: fixture + APPROX_VIEWPORTS + endpoints virtuales para debug de wires)

## Decisions

- Waste 10% se aplica en `compute_bom`, no en `WireRun.total_length_ft` (ese campo = plan + vertical)
- Encadenado por grafo de proximidad (dirección solo como tie-break); cortes duros de dirección rompían runs largos
- Componentes chicos (&lt;3 dashes y &lt;20 pt ink) se descartan como fragmentos de símbolos
- 4+ gang → precio de `box_3gang` (SKU más cercano listado)

## Needs from Santiago

Precios Home Depot / Lowe’s aún **sin verificar** (dejar `unit_price` o confirmar URL/precio):

- `box_3gang`, `plate_3gang`
- `switch_three_way` (precio tentativo 2.58, marked unverified), `switch_dimmer`, `switch_fan`, `switch_other`
- `receptacle_duplex`, `receptacle_gfci`, `receptacle_other`
- `device_ceiling_fan`, `device_light`, `device_exhaust_fan`, `device_detector`

## Explicación para Santiago

Construí el módulo extra de lista de materiales. Primero medí en el plano real cuánto mide cada rayita de los cables dibujados (unas 7 pt de trazo y 4 pt de hueco). Con eso el código junta las rayitas en “corridas” de cable, las pega a los dispositivos cercanos y calcula pies de cable 14/2 o 14/3 (14/3 solo entre switches de 3 vías). También agrupa interruptores vecinos en cajas de 2 o más gangs, elige tapa normal o weatherproof, y arma una lista de materiales con precios de Home Depot cuando pude verificarlos (si no, dejo el precio vacío para que no inventemos números). Todo es función pura: si en la web mueves un switch, el backend puede recalcular cajas, cable y total al instante.
