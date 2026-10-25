# Cómo contar a mano (ground truth)

Instrucciones para Santiago. El objetivo es una verdad de referencia **independiente**
del sistema: así sabemos si el takeoff funciona de verdad.

## Antes de empezar

1. Abre `data/plans/escondido_plans.pdf` (cada página = un plan).
2. Ten a mano `coordination/DECISIONS.md` (reglas de conteo).
3. Edita solo `eval/ground_truth/planN.counts.yaml` del plan que estás contando.
4. **No mires** la salida del sistema (overlays, JSON, UI, reportes) mientras cuentas.
   Si ya viste un resultado, deja pasar un rato o cuenta otro día.

## Por cada plan (páginas 1–4)

1. Localiza el dibujo **ELECTRICAL PLAN - PLAN N** (no el mechanical ni el finish).
2. Lee la **LEGEND** de esa hoja: cada símbolo y letra (`D`, `F`, `3D`, `GFI`, `VP`, …).
3. Recorre el plano eléctrico y marca cada componente en el YAML de su habitación.
4. Usa las claves `category.subtype` ya listadas (todas empiezan en `0`). Sube el número
   cuando encuentres uno. No inventes claves nuevas.

## Habitaciones

- Los nombres del template vienen de la SPEC (sección 1), en forma legible
  (ej. `Kitchen / Dining`, `CL 1` / `CL 2` si hay dos closets).
- **Attic**: lo que está dentro del recuadro "IN ATTIC".
- **Exterior**: fuera del edificio (luz de porche, receptáculo WP, etc.).
- Cocina y comedor: **una sola** habitación si el plano dice `KITCHEN / DINING`
  (planes 1 y 3); **separadas** si hay etiquetas distintas (plan 2).

## Reglas rápidas (detalle en DECISIONS.md)

1. Un fan/luz combinado o smoke/CO cuenta **una vez** en su tipo combinado.
2. El símbolo de ceiling fan con `J` en el centro = **un** ceiling fan, no fan + junction box.
   Un `J` solo = junction box.
3. El tipo de switch lo define la letra junto al símbolo (según la leyenda de esa hoja).
4. No cuentes plumbing (CW, HW, …), el panel de attic access, ni símbolos del plano mecánico.

## Cuando termines un plan

1. Guarda el YAML.
2. Opcional (después, con revisión visual): exporta posiciones a
   `eval/ground_truth/planN.detections.json` para precision/recall por detección.
3. Avisa a Agente 7 para regenerar el reporte: `make eval` (cuando Agente 1 conecte el CLI).
