# Agente 6 — Frontend (web/)

## Estado

BOM tab polish: total grande + Assumptions colapsable con labels humanos.

## Hecho

- Total BOM destacado arriba (`data-testid="bom-total"`)
- Assumptions colapsado por defecto: `Assumptions (N) ▸`; expandido scrollea en `max-h-40` sin empujar las líneas
- Labels: Ceiling height, Switch box height, Slack per end, Waste %, Cable roll
- Notas de pricing + routing como oraciones; ocultos `dash_length_pt_median` / `gap_pt_median`
- Antes: colores de cable, handles, Edit cables en header, Fixtures (allowance)

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm run build
pnpm dev
# Sheet → BOM: total grande; Assumptions colapsado; clic para expandir
```

## Siguiente

- (ninguno)

## Bloqueos

- Ninguno

## Decisions

- Conteo del badge = filas visibles tras filtrar claves técnicas
- Cuerpo expandido `max-h-40` + overflow para no robar el scroll de las líneas

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

En la pestaña BOM el total ahora se ve grande arriba. Las Assumptions ya no ocupan
media pantalla: vienen cerradas (`Assumptions (6) ▸`) y al abrirlas scrollean solas
abajo, sin tapar la lista. En vez de claves crudas ves textos claros (altura de
cielo, caja de switch, slack, desperdicio, rollo) y las notas de precio/ruta como
frases cortas. Los números técnicos de dash/gap solo quedan en el Excel.
