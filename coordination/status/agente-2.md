# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

**Round 7b done** (final engine fix). Plan 1 IN ATTIC circle-with-cross light is in `analyze_sheet` with room Attic. Ask A1 to bump patch.

## Hecho

| Fix | Behavior | Commit |
|-----|----------|--------|
| R7.1–2 | Attic + sink half-hot (first pass) | `273d3e7` |
| R7.3 | Viewport/legend generalization | `d4cc92d` |
| R7b | `_attic_boxes` uses gray **stroke** rectangle (~1097–1142 × 419–452); emit circle-ring light @~(1117.4, 435.8) with room Attic. Padded-label bbox had stolen the hallway can @~(1120, 409) and skipped the real glyph. | *(this commit)* |

### Verify (CLI, no LLM)

```bash
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
```

Plan 1: **10 lights**; one with notes `attic_panel_light` / `attic_circle_ring` at ~(1117, 436), room **Attic**.

Test: `test_plan1_has_light_whose_room_is_attic`.

### Note for Agente 3

Attic room polygon is still ~(1084, 405)–(1151, 442) — covers the hallway can above the panel and cuts before the panel bottom (y≈452). Please tighten Attic to the gray stroke frame. A2 symbols no longer depend on the padded label for the light itself.

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/test_attic_and_halfhot_r7.py -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
```

## Siguiente

- Agente 1: bump `PIPELINE_VERSION` patch + push
- Agente 3: tighten Attic polygon to gray stroke panel (optional cleanup of false Attic on hallway can @~1120,409)

## Bloqueos

- Push only Agente 1.

## Decisions

- IN ATTIC panel geometry = gray stroke rectangle first; gray fill second; padded label last.
- Prefer circle-ring recovery inside the panel over square-frame recessed scan (hallway cans).

## Needs from Santiago

- Confirm overlay: light marker on circle-with-cross inside IN ATTIC box; A1 bump + push.

## Explicación para Santiago

El panel IN ATTIC del plan 1 está dibujado con un rectángulo de líneas grises (~45×33 pt), no con un relleno. Antes usábamos un padding alrededor del texto «ATTIC», que entraba en la lata del pasillo de arriba y hacía que el motor creyera que ya había luz en el ático — y se saltaba el círculo con cruz de dentro del box. Ahora el bbox del panel sale de esas cuatro líneas grises, detectamos el anillo del círculo con cruz (~1117, 436) y queda con habitación Attic. El test y el CLI sin LLM lo confirman. Pedir a Agente 1 el bump de versión.
