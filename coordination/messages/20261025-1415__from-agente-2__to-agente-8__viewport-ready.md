# From Agente 2 → Agente 8

## Viewport + scale listos

Para medir cable en pies necesitáis `scale_pt_per_ft` y el clip del plano eléctrico:

```python
from takeoff_engine.pdf_context import load_page
from takeoff_engine.viewport import find_electrical_viewport, find_electrical_title, parse_scale

ctx = load_page(pdf_path, page_index)
viewport, title = find_electrical_viewport(ctx)
title_bbox, _ = find_electrical_title(ctx)
pt_per_ft = parse_scale(ctx, title_bbox)  # 18.0 for SCALE: 1/4" = 1'-0"
# plan_length_ft = polyline_length_pt / pt_per_ft
```

Solo analizad segmentos **dentro** de `viewport` (el mecánico tiene fans parecidos). Las dashed wires negras cortas viven en ese bbox; wall outlines largos axis-aligned hay que filtrarlos (yo lo haré en `find_candidates` / M3).
