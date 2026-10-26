# Agente 5 — Backend API, jobs, database

## Estado

Exports Excel/PDF listos. Pedido a Agente 1: `openpyxl` + `reportlab` en `backend/pyproject.toml`.

## Hecho

- API completa (upload, jobs, CRUD, review, file_hash, job fields en document)
- **Exports:** `export.xlsx` / `quote.pdf` a nivel sheet y document
- Tests unitarios abren xlsx/pdf; mensaje a Agente 6

## Cómo probarlo

```bash
# Tras Agente 1: uv sync (openpyxl, reportlab)
uv run pytest backend/tests/test_exports.py -q -k "not endpoints"
# Con Postgres:
uv run pytest backend/tests/test_exports.py -q
```

## Siguiente

- Confirmar deps de Agente 1 en pyproject
- Agente 6: botones de descarga

## Bloqueos

- `openpyxl` / `reportlab` aún no están en `backend/pyproject.toml` (pedido a Agente 1);
  instalados localmente con `uv pip` para desarrollo

## Decisions

- Document workbook: una sola pestaña por tipo con columna `Plan`
- Quote PDF: una sección/página por hoja; overlay a 72 dpi

## Needs from Santiago

- Ninguno urgente

## Explicación para Santiago

Ahora puedes bajar un Excel con el takeoff por cuarto, detecciones, BOM, cables,
supuestos y correcciones, y un PDF de cotización limpio con totales y una imagen del
plano. También hay exportación de las 4 hojas juntas (un Excel y un PDF).
