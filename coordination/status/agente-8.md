# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

Wires **v2.1**: dash-gap only (no symbol outlines / fan blades); plan 1 ≈19 runs; `nm_14_3` travelers restored where ≥2 gangs exist.

## Hecho

- Reject continuous glyph strokes (gap < 1.2 pt); require dash gap pattern
- Exclude ink in receptacle/detector/exhaust bboxes (+2 pt) and fan blade disks
- Drop closed loops; require different end devices; plan length ≤ 40 ft
- Traveler BFS + on-curve max-separation 3-way pair → `nm_14_3`
- Tests: plan 1 count band, no >40 ft total, no same-end; all-plans validity
- Debug PNGs: `out/debug/wires_plan{1..4}.png`
- Asked Agente 1 to bump `PIPELINE_VERSION` (Santiago-approved)

## Run counts (v2.1)

| Plan | runs | nm_14_2 (n / ft) | nm_14_3 (n / ft) |
|------|------|------------------|------------------|
| 1    | 19   | 18 / 222.9       | 1 / 33.2         |
| 2    | 23   | 23 / 265.2       | 0 / 0.0*         |
| 3    | 48   | 44 / 638.8       | 4 / 128.4        |
| 4    | 53   | 51 / 677.5       | 2 / 65.5         |

\*Plan 2 detections have only **one** 3-way — cannot emit a traveler pair (needs Agente 2).

Plan 1: 0 fan-blade runs, 0 same-end loops, max total 33.2 ft.

## Cómo probarlo

```bash
.venv/Scripts/python -m pytest engine/tests/bom/test_wires.py -v
.venv/Scripts/python engine/tests/bom/render_debug.py
```

## Siguiente

- Plan 2 second 3-way detection (Agente 2) if Santiago wants nm_14_3 there
- Unverified prices

## Bloqueos

- Agente 1 version bump

## Decisions

- Gap < 1.2 = continuous glyph (never wire); dash gaps start at 1.2
- Outline bbox exclude: fan / receptacle / detector / exhaust only (not lights/switches — those punch traveler paths)
- Fan blade disk: 0.65 × max(bbox side) + 12 pt

## Needs from Santiago

None for this fix. Optional: confirm plan 2 should have two 3-ways in detections.

## Explicación para Santiago

Los cables ya no siguen el dibujo del ventilador ni los circulitos de los tomacorrientes. Solo cuento rayitas **discontinuas** (con hueco de verdad entre ellas); lo que está pegado (contorno de símbolo) se ignora. También saco la tinta dentro de ventiladores / tomas / detectores / extractores. En el Plan 1 quedan ~19 corridas, sin bucles raros, y el traveler 3-way vuelve como `nm_14_3`. El Plan 2 solo tiene un 3-way detectado, así que ahí no hay par para 14/3.
