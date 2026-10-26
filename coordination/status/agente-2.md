# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

**Engine freeze ready.** Final pass: Bed-2 AFI wall receptacles + exhaust/light dedupe. No further engine changes unless Santiago asks.

## Hecho

### Final freeze commits (this round)

| Fix | Behavior |
|-----|----------|
| AFI wall receptacles | Keep coded receptacles/switches when rooms mis-label Exterior; text-anchored `AFI`/`AFCI` recovers duplexes swallowed by megas |
| Exhaust ↔ light NMS | Overlapping bath exhaust + false recessed → keep exhaust only |

### Counts (`--no-llm --no-bom`)

| plan | light | fan | sw | rec | AFI orphans |
|------|-------|-----|----|-----|-------------|
| 1 | 10 | 1 | 12 | 26 | 0 |
| 2 | 13 | 2 | 10 | 33 | 0 |
| 3 | 13 | 2 | 12 | 33 | 0 (was 3 on Bed 2) |
| 4 | 16 | 3 | 15 | 41 | 0 (was 2) |

Regression: plan 3 light minimum set to ≥13 after removing exhaust double-counts (was 15 with duplicates).

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 3 --out out/plan3.json --debug --no-llm --no-bom
```

## Siguiente

- Agente 1: bump patch + push; engine freeze for Agente 2 paths
- Agente 7: final eval

## Bloqueos

- Push only Agente 1.

## Decisions

- Plan 3 light floor ≥13 (deduped); switches floor still ≥11.
- AFI text-anchor mirrors SD/EXT pattern when clustering swallows the glyph.

## Needs from Santiago

- Confirm engine freeze; A1 bump + push.

## Explicación para Santiago

Último retoque antes del freeze: en el plan 3 faltaban tomacorrientes AFI en las paredes de Bed 2 porque rooms los marcaba como Exterior y los tiraba el filtro; ahora se conservan si tienen código de dispositivo, y si un blob enorme se come el símbolo, lo anclamos al texto AFI (igual en los 4 planos). En Bath 2 el exhaust y una “recessed” falsa ya no se solapan: gana el exhaust. Con esto el motor de símbolos queda congelado salvo que pidas otro cambio.
