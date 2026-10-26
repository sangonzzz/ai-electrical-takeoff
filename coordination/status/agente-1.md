# Agente 1 — Lead / architecture / integration

## Estado

v0.3.0: una sola `PIPELINE_VERSION`, `ENGINE=real` por defecto, tag listo.

## Hecho

- `PIPELINE_VERSION = __version__ = "0.3.0"` solo en `engine/takeoff_engine/__init__.py`
- `pipeline.py` importa esa constante (ya no `0.2.0-a2`)
- CLI `takeoff --version` + analyze imprime `pipeline_version`
- AGENTS.md §13: bump patch en todo cambio de comportamiento del engine
- `docker-compose.yml` + `.env.example`: `ENGINE=real` (fake solo tests)
- CHANGELOG v0.2.0 / v0.3.0; mensajes a A2, A3, A5, A8

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.3.0
uv run python -c "from takeoff_engine import PIPELINE_VERSION; assert PIPELINE_VERSION=='0.3.0'"
# SheetResult.pipeline_version must match after analyze
```

## Siguiente

- Tras cada cambio de engine de A2/A3/A4/A8: bump patch + commit/tag si aplica
- Pushear CI cuando haya scope `workflow`

## Bloqueos

- Token `gh` sin scope `workflow` para Actions (CI local only)

## Decisions

Ver DECISIONS.md (PIPELINE_VERSION única, ENGINE=real).

## Needs from Santiago

- (ninguno nuevo para este fix)

## Explicación para Santiago

Antes el CLI decía una versión (`0.2.0-a2`) y el backend otra (`0.1.0`), así que al re-subir el mismo PDF el sistema podía creer que el análisis “ya estaba” con una versión vieja. Ahora hay **una sola** versión `0.3.0` en un solo archivo; CLI, JSON del motor y la clave de idempotencia del backend usan la misma. Si alguien cambia cómo se detectan símbolos o cuartos, hay que subir al menos el número de parche para forzar un análisis nuevo. Docker y `.env` arrancan con el motor **real** (el fake queda para tests).
