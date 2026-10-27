# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

Lista de precios Home Depot 2026-10-27 verificada; BOM por subtype (sin `*_other`); sección **Fixtures (allowance)**. Análisis/golden intacto.

## Hecho

- `data/price_list.yaml`: SKUs verificados (dimmers, fan switch, vacancy, timer, 3-way, receptáculos duplex/GFCI/AFCI/240V, box/plate 3G, fan, luces, exhaust, detector)
- `bom.py`: map por subtype; `group_bom_lines` → Devices / Fixtures (allowance) / Boxes and plates / Cable
- Notas en `assumptions.yaml` (240V GFCI en breaker; smoke como combo; fixtures allowance)
- Tests bom/pricing verdes; sin tocar `find_wire_runs` / `PIPELINE_VERSION`
- Mensajes a Agente 5 (quote PDF sections) y Agente 6 (BomPanel fixtures)

## Cómo probarlo

```bash
uv run --package takeoff-engine pytest engine/tests/bom/ -q
```

## Siguiente

- Agente 5: encabezados de sección en quote.pdf vía `group_bom_lines`
- Agente 6: sección Fixtures en BomPanel
- Pendant sigue `verified: false` (sin SKU)

## Bloqueos

Ninguno.

## Decisions

- Pack prices → per-each (duplex 2.60, GFCI 17.66)
- `three_way_dimmer` comparte SKU Lutron Diva con `dimmer`
- Pendant sin precio verificado (queda null)
- Secciones sin campo en contrato: helper + orden de líneas

## Needs from Santiago

Confirmar pack size Lithonia WF4 si no es unitario.

## Explicación para Santiago

Actualicé la lista de precios con lo que capturaste en Home Depot el 27/10 y dejé de meter switches/receptáculos raros en un balde “other”: cada subtype tiene su SKU. Los fixtures (ventiladores, luces, extractores, detectores) van en una sección aparte “Fixtures (allowance)” para el BOM y, cuando Agente 5/6 lo cableen, también en el PDF y el panel. El análisis del plano no cambió, así que el golden sigue válido.
