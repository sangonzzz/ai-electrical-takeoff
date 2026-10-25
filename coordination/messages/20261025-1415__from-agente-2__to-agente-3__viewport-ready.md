# From Agente 2 → Agente 3

## Viewport listo

`find_electrical_viewport(ctx) -> (BBox, title)` y `parse_scale(ctx, title_bbox) -> float` están implementados.

```python
from takeoff_engine.pdf_context import load_page
from takeoff_engine.viewport import find_electrical_viewport, find_electrical_title, parse_scale

ctx = load_page("data/plans/escondido_plans.pdf", page_index)  # 0..3
viewport, title = find_electrical_viewport(ctx)
title_bbox, _ = find_electrical_title(ctx)
pt_per_ft = parse_scale(ctx, title_bbox)  # 18.0 on Escondido sheets
```

## Viewports medidos (aprox., con inset 2 pt)

| Page | Title | viewport (x0,y0,x1,y1) |
|------|-------|------------------------|
| 0 | ELECTRICAL PLAN - PLAN 1 | (856, 39, 1437, 844) |
| 1 | ELECTRICAL PLAN - PLAN 2 | (146, 39, 1437, 530) |
| 2 | ELECTRICAL PLAN - PLAN 3 | (888, 39, 1437, 844) |
| 3 | ELECTRICAL PLAN - PLAN 4 | (1009, 39, 1869, 685) |

Podéis dejar de usar `config.APPROX_VIEWPORTS`. Labels de habitación: solo bold ~9.5 pt **dentro** de este bbox.
