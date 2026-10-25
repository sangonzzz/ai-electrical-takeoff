# Cómo obtener ground truth

Hay **dos** caminos. El preferido ahora es revisar en la app; el conteo a ciegas
sigue siendo útil para calibrar el sesgo de la revisión.

## Camino A (preferido): revisión humana en la app

1. Corre el takeoff sobre el PDF y abre el plano eléctrico en la UI.
2. Corrige marcas: borra falsos positivos, agrega los que faltan, cambia tipo/cuarto.
3. **Mitiga el sesgo de aceptar lo dibujado:** revisa **una categoría a la vez** con
   el filtro de la UI (primero `ceiling_fan`, luego `light`, luego el resto).
4. Exporta la verdad revisada:
   `GET /api/sheets/{id}/ground-truth.json`
   y guárdala como `eval/ground_truth/planN.detections.json`.
5. (Opcional) Guarda también el log:
   `GET /api/sheets/{id}/corrections` → `eval/ground_truth/planN.corrections.json`
   (o deja `corrections` dentro del JSON de ground-truth).
6. Corre eval contra el resultado **antes** de las correcciones (pipeline /
   `--results-dir`), no contra la hoja ya editada.

## Camino B: conteo a mano sin mirar el sistema

Instrucciones para una verdad **independiente** de la UI (útil en la entrevista
y para detectar el sesgo del camino A).

### Antes de empezar

1. Abre `data/plans/escondido_plans.pdf` (cada página = un plan).
2. Ten a mano `coordination/DECISIONS.md` (reglas de conteo).
3. Edita solo `eval/ground_truth/planN.counts.yaml` del plan que estás contando.
4. **No mires** la salida del sistema (overlays, JSON, UI, reportes) mientras cuentas.

### Por cada plan (páginas 1–4)

1. Localiza el dibujo **ELECTRICAL PLAN - PLAN N** (no el mechanical ni el finish).
2. Lee la **LEGEND** de esa hoja.
3. Recorre el plano y marca cada componente en el YAML de su habitación.
4. Usa las claves `category.subtype` ya listadas (empiezan en `0`).

### Habitaciones

- Nombres del template = `display_name` del motor (ej. `Kitchen / Dining`,
  `CL 1`…, `Laundry`, `Attic`, `Exterior`).
- Cocina/comedor: una sola habitación si el plano dice `KITCHEN / DINING`
  (planes 1 y 3); separadas en el plan 2.

### Reglas rápidas (detalle en DECISIONS.md)

1. Un fan/luz o smoke/CO combinado cuenta **una vez**.
2. Ceiling fan con `J` en el centro = un fan (no fan + junction box).
3. Tipo de switch = letra según la leyenda de esa hoja.
4. No cuentes plumbing ni el plano mecánico.

### Cuando termines

Guarda el YAML y avisa para regenerar el reporte (`uv run takeoff eval`).
