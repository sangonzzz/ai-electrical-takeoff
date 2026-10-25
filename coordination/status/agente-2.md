# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

Precision round 2 listo (fixes 1–8). Overlays regenerados en `out/debug/`.

## Hecho

### Round 1
- Strip dashes before cluster; wall+$ switch gate; recessed force; keynotes; X markers; fan J+blades; SD tokens

### Round 2
1. `junction_box` only small circle + `J` (not fan hub) → JB count 0 on Escondido
2. Text-anchored SD/SD/MA → center-dot (~12 pt); plan 4 has 5 detectors
3. `EXT` → `exterior_wall` light
4. Half-fill circle (no duplex slots) → exhaust; `IAQ` → indoor_air_quality (plan 1 bath found)
5. Duplex half-fill → `afci_half_hot` (plan 1 kitchen)
6. Cross NMS: detector beats overlapping recessed light
7. Wall light = circle+cross+tick (bath vanity)
8. IN ATTIC panel: wall-mask edges + switch IoU relax + center nudge → Attic room

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -v
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
# pages 1..4; overlays out/debug/detections_p{1..4}.png
```

## Siguiente

- Receptacle over-count if eval demands
- Clustering speed on dense sheets

## Bloqueos

- Ninguno. Pedir a Agente 7 re-run eval.

## Decisions

- JB: never template-only; geometry = circle containing `J`, outside fan bbox.
- SD: token is authoritative; place at center-dot fill, not at text.
- Half-disc: 2 duplex slots → half-hot; 4 circle chords → exhaust.
- Cross-NMS only for known collisions (detector/light, exhaust/half-hot).
- Attic: panel outline joins wall mask; ≤1 switch per panel.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

En la segunda pasada eliminamos las “cajas de unión” falsas (solo vale un círculo chico con J, no el hub del abanico). Los detectores se anclan al texto SD/SD/MA y al puntito negro de al lado — por eso el plan 4 ya no pierde los de los dormitorios. EXT marca la luz exterior; el extractor del baño es el semicírculo sin las dos rayitas de un tomacorriente; el half-hot de cocina es el semicírculo *con* esas rayitas. Si una luz empotrada cae encima de un SD, nos quedamos con el detector. La luz del tocador del baño es wall (círculo + cruz + patita). Y lo del cajón IN ATTIC (luz y switch) ya se detecta y cae en la habitación Attic.
