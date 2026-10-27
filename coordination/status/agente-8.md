# Agente 8 — Bill of materials (wires, boxes, bom, pricing)

## Estado

Wires **v3**: black dashes only; keynotes + gray millwork excluded; DF→fan restored; `nm_14_3` = 3-way travelers only.

## Hecho

- **Black (0,0,0) only** — never `gray_segments` / RGB ~0.67 (cabinets, sinks, toilets, equipment)
- Exclude **keynote boxes** (A01/B38/…, size ≤12 pt)
- Exclude black dashes whose midpoint sits in large **gray millwork fills**
- Dropped oversized fan-blade disk (it ate bedroom D/F→fan); blades still rejected by gap pattern
- **Cable rule documented:** `nm_14_3` only 3-way↔3-way traveler; switch→light / light→light → `nm_14_2`
- Tests + docs + assumptions updated; debug PNGs regenerated
- Asked Agente 1 to bump `PIPELINE_VERSION`

## Run counts (v3)

| Plan | runs | nm_14_2 (n / ft) | nm_14_3 (n / ft) |
|------|------|------------------|------------------|
| 1    | 20   | 19 / 240.8       | 1 / 33.2         |
| 2    | 27   | 27 / 316.9       | 0 / 0.0*         |
| 3    | 52   | 48 / 709.1       | 4 / 139.5        |
| 4    | 61   | 59 / 737.8       | 2 / 65.5         |

\*Plan 2: only one 3-way in detections. Plan 1 has switch→fan run; 4 keynotes excluded.

## Cómo probarlo

```bash
.venv/Scripts/python -m pytest engine/tests/bom/test_wires.py -v
.venv/Scripts/python -c "from takeoff_engine.wires import find_wire_runs; ..."
```

PNGs: `out/debug/wires_plan{1..4}.png`

## Siguiente

- Reviewer visual pass on all 4 PNGs
- Plan 2 second 3-way (Agente 2) if needed

## Bloqueos

- Agente 1 version bump

## Decisions

- Strict black RGB ≤ 0.02; gray millwork never candidates
- No fan bbox/disk blanking (approach wiring enters fan bbox)
- Keynote size cutoff 12 pt (Escondido tags ~9.5 pt)

## Needs from Santiago

None.

## Explicación para Santiago

v3: solo rayitas **negras** cuentan como cable (las grises de gabinetes/inodoros/B38 no). Sacamos también las cajitas de keynotes y la tinta negra que cae sobre rellenos grises de millwork. Quité el disco enorme del ventilador que se comía el cable D/F→fan del bedroom. Regla de tipo: `nm_14_3` **solo** entre dos 3-way; todo lo demás (apagador→luz, luz→luz) es `nm_14_2`.
