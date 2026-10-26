# Agente 1 — Lead / architecture / integration

## Estado

Engine freeze en **v0.4.0**. Cambios de motor solo con aprobación de Santiago.

## Hecho

- `PIPELINE_VERSION` → `0.4.0` + tag
- CHANGELOG: precision rounds 3–5, geometric recessed, 3-way cables, per-plan regression guard
- AGENTS.md §14 + DECISIONS: freeze del engine
- Mensaje to-all

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.4.0
git show v0.4.0 --no-patch
```

## Siguiente

- Integración / demo / CI; no tocar engine salvo que Santiago lo pida
- Pushear CI cuando haya scope `workflow`

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Engine freeze v0.4.0 (AGENTS.md §14).

## Needs from Santiago

- (ninguno para este tag)

## Explicación para Santiago

Marqué el motor en **0.4.0**: es la versión que incluye las rondas de precisión 3–5, la regla geométrica de luces empotradas, cables 14/3 entre 3 vías, y el guard de regresión por plano. A partir de aquí el código del engine (detección, cuartos, LLM, BOM, overlay) **no se cambia** sin tu OK; si un agente quiere tocar algo, me escribe y yo solo subo versión después de que apruebes. Así la demo y la idempotencia del backend no se mueven debajo de tus pies.
