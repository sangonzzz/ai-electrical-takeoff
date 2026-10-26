# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

Round 4 listo: false lights on plan 4 cut (28 → 13). Overlays 1–4 regenerados.

## Hecho

### Round 4 commits

| Commit | Fix |
|--------|-----|
| `f50e91f` | Never emit a light at a ceiling-fan hub `J` (peel skip + suppress + cross-NMS) |
| `4b68d3d` | High light-template score; no cabinet/appliance false lights; tighter peel rings |
| `dc80a21` | Outside footprint only EXT/WP (after room assign) |
| (this) | Category-count regression test + docs/status |

### Plan 4 after R4 (`--no-llm --no-bom`)

- lights **13** (was 28): no hub lights at Bed 1/2/Opt3 fans
- fans centered on J: (1711.3,208.1), (1711.3,459.9), (1232.0,459.9)
- EXT porch light kept; top-left margin false recessed gone
- Bath 2 wall @ (1450,474) kept; hallway peel @ (1564,321) kept

### Plan 1 baseline counts

sw 12, fan 1, light 8, rec 24, exhaust 2, detector 2

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 4 --out out/plan4.json --debug --no-llm --no-bom
# overlays: out/debug/detections_p{1..4}.png
```

## Siguiente

- Agente 1: bump pipeline patch version + push R3–R4 commits
- Agente 7: re-eval after push

## Bloqueos

- Push still Agente 1 only.

## Decisions

- Shape-forced lights need light-legend IoU ≥0.55 (peeled rings ≥0.40).
- Peel rings capped at 40 shorts / aspect ≤1.35 so kitchen megas do not spawn cans.
- Receptacle codes (GFI/240V/AFI/…) block weak "lights".
- Exterior filter runs after `assign_rooms` via `drop_outside_footprint`.

## Needs from Santiago

- Ask Agente 1 to bump patch version (message filed).

## Explicación para Santiago

En el round 3 las luces del plan 4 se duplicaron (14→28): salían “recessed” falsas en el hub J de los abanicos, en gabinetes/fregaderos de cocina y baños, y una fuera del edificio arriba a la izquierda. Ahora: (1) el círculo con J del abanico es solo del abanico; (2) forzar luz por forma exige un match alto con la leyenda y no dispara dentro de arquitectura gris ni con códigos de tomacorriente; (3) fuera del footprint solo quedan ítems EXT/WP; (4) un test de regresión por categorías evita que se vuelva a duplicar en silencio.
