# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

Round 3 (plan 4 UI review) listo. Overlays 1–4 regenerados.

## Hecho

### Round 3 commits

| Commit | Fix |
|--------|-----|
| `e8fff76` | Peel recessed circles trapped in hallway/attic mega-blobs |
| `32c809d` | Circle-in-square on wall → light unless duplex (kitchen sink) |
| `9e8be0e` | Elongated wall lights (Bath 2 vanity + tick) |
| `1605c33` | Ceiling-fan marker center = `J` hub |

### Plan 4 spot checks

- Hallway cans near IN ATTIC: recessed @ (1538,322) and (1564,321)
- Kitchen sink: recessed @ (1495,136)
- Bath 2 wall: `wall` @ (1450,474)
- Fans centered on J: (1711.3,208.1), (1711.3,459.9), (1232.0,459.9)

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 4 --out out/plan4.json --debug --no-llm --no-bom
# overlays: out/debug/detections_p{1..4}.png
```

## Siguiente

- Agente 1 push if origin still behind
- Agente 7 re-eval after push

## Bloqueos

- Push still Agente 1 only.

## Decisions

- Mega-clusters: peel ~12 pt short-stroke rings back out as light candidates.
- Near-wall circle without duplex slots = light (not receptacle).
- Wall light allows denser clusters (n≤90) when aspect≥1.5 + cross + tick.
- Fan `Detection.center` = hub `J` coordinates; bbox stays the blade cluster.

## Needs from Santiago

- (ninguno) — A1 push when convenient.

## Explicación para Santiago

En el plan 4 faltaban dos luces del pasillo junto al ático porque el panel las tragaba en un blob enorme: ahora las “pelamos” como círculos aparte. La del fregadero de cocina se confundía con un tomacorriente de pared; si no tiene las dos rayitas de duplex, es luz. La del baño 2 (círculo con patita al espejo) ya sale como wall. Y el abanico de Bed 1 ya no queda corrido: el marcador va en la J del hub en todos los abanicos.
