# Agente 1 — Lead / architecture / integration

## Estado

**v0.5.1** tagged (`PIPELINE_VERSION` patch bump).

## Hecho

- `PIPELINE_VERSION` → `0.5.1` + CHANGELOG + tag
- README version refs updated

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.5.1
git show v0.5.1 --no-patch
```

## Siguiente

- Rebuild api/worker image if stack is running: `docker compose up -d --build api worker`

## Bloqueos

- Token `gh` sin scope `workflow` para Actions

## Decisions

Ninguna nueva.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Subí el motor a **0.5.1** (parche) para que al re-subir un PDF el backend no reutilice corridas de 0.5.0 si el engine ya cambió después de ese tag. El tag `v0.5.1` está en GitHub.
