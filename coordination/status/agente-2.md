# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

M1 listo (viewport + scale). Siguiente: M2 leyenda.

## Hecho

- `viewport.find_electrical_viewport` / `find_electrical_title` / `parse_scale`
- Tests: 4 páginas (título + scale 18.0) y page 1 excluye mechanical `(500,450)`
- Debug PNGs: `out/debug/viewport_p{1..4}.png` (revisados a ojo)

## Cómo probarlo

```bash
uv sync --all-packages --group dev
uv run pytest engine/tests/symbols/test_viewport.py -v
# Debug (regenerar PNGs):
uv run python -c "from pathlib import Path; import pymupdf; from PIL import Image, ImageDraw; from takeoff_engine.pdf_context import load_page; from takeoff_engine.viewport import find_electrical_viewport, find_electrical_title, parse_scale; pdf=Path('data/plans/escondido_plans.pdf'); out=Path('out/debug'); out.mkdir(parents=True, exist_ok=True); doc=pymupdf.open(pdf); mat=pymupdf.Matrix(0.5,0.5); 
"
```

O abrir directamente `out/debug/viewport_p1.png` … `viewport_p4.png`.

## Siguiente

- M2: `extract_legend` + `legend_templates` + debug + mensaje a Agente 4

## Bloqueos

- Ninguno

## Decisions

- Celdas del sheet: solo líneas verticales negras con tramo *por encima* del título (Plan 4: el divisor en x≈1439 empieza debajo del título; hay que ignorarlo para no cortar el plano eléctrico).
- Viewport bottom = `title.y0` (el dibujo está arriba del título + SCALE).
- Título se busca en **spans** (una sola cadena `ELECTRICAL PLAN - PLAN N`), no en words tokenizados.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

En cada hoja hay tres planos (eléctrico, mecánico, finishes) separados por líneas de marco. Busco el título grande en negrita "ELECTRICAL PLAN - PLAN N", luego las líneas verticales largas que llegan *arriba* de ese título, y tomo la celda entre la vertical de la izquierda y la de la derecha. El viewport es esa celda por encima del título. Así en la página 1 el punto (1150,450) cae dentro y el (500,450) del plano mecánico queda fuera. La escala se lee del texto `SCALE: 1/4" = 1'-0"` debajo del título y da 18 puntos por pie. Todo es geometría vectorial, sin adivinar coordenadas con la IA.
