# Agente 1 — Lead / architecture / integration

## Estado

**v0.5.0** tagged. Backend exports deps (`openpyxl`, `reportlab`) en pyproject.

## Hecho

- `PIPELINE_VERSION` → `0.5.0` (round 6 + LLM rules + wires v2, aprobado Santiago)
- CHANGELOG + tag `v0.5.0`
- `backend/pyproject.toml`: `openpyxl`, `reportlab` (pedido A5)
- `uv lock` / sync

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.5.0
uv sync --all-packages --group dev
uv run python -c "import openpyxl, reportlab; print('exports ok')"
```

## Siguiente

- Rebuild backend image: `docker compose up -d --build api worker`
- A6: botones de descarga export si aún faltan

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

v0.5.0 es bump de motor aprobado; freeze sigue: más cambios de engine solo con OK de Santiago.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Subí el motor a **0.5.0** (ronda 6, reglas LLM y cables v2) para que el backend no reutilice análisis viejos de 0.4.0. También agregué `openpyxl` y `reportlab` al backend para los Excel/PDF de cotización que pidió Agente 5. Tag `v0.5.0` en GitHub.
