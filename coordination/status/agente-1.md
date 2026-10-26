# Agente 1 — Lead / architecture / integration

## Estado

README + architecture finales (fase 2 paso 6). Engine freeze **0.4.0**. Docker imagen backend OK.

## Hecho

- `README.md`: qué es, Docker, CLI/eval, Claude (sin coordenadas), conteos → DECISIONS, versionado, límites, placeholder Accuracy results
- `docs/architecture.md`: Mermaid componentes + flujo upload→ARQ→engine→Postgres→UI→corrections
- Docker api/worker con `/opt/venv` (commit previo)
- Engine **no** tocado

## Cómo probarlo

```bash
# docs
# open README.md and docs/architecture.md
docker compose ps
uv run takeoff --version   # 0.4.0
```

## Siguiente

- Agente 7 llena “Accuracy results” tras conteos a mano
- CI workflow cuando haya scope `workflow`

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Ninguna nueva en este paso (docs only).

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Dejé el README y la arquitectura listos para la entrevista/demo: qué hace el sistema, cómo se corre con Docker, cómo se usa el CLI y el eval, por qué Claude no da coordenadas, dónde están las reglas de conteo, cómo versionamos el motor (`0.4.0` congelado), y un espacio vacío “Accuracy results” para que Agente 7 pegue las métricas cuando tengas los conteos a mano. Los diagramas Mermaid muestran el camino completo: subís el PDF → cola ARQ → motor → Postgres → UI → log de correcciones.
