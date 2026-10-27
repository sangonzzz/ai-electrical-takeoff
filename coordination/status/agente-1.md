# Agente 1 — Lead / architecture / integration

## Estado

**v1.0.0** interview release — engine `0.6.7` + app frozen.

## Hecho

- `PIPELINE_VERSION` → `0.6.7` + CHANGELOG known limits + DECISIONS / AGENTS freeze
- Verified green: `uv run pytest` **183 passed**; web `tsc` + `pnpm build` OK
- Tags: `v0.6.7`, **`v1.0.0`** (interview release)
- Mensaje to-all

## Cómo probarlo

```bash
uv run takeoff --version   # -> 0.6.7
git show v1.0.0 --no-patch
uv run pytest -q
cd web && pnpm run build
```

## Siguiente

- Solo docs / tests locking current behavior unless Santiago unfreezes

## Bloqueos

- Token `gh` sin scope `workflow` para Actions (`.github/` may still be untracked)

## Decisions

Interview freeze at v1.0.0 / PIPELINE 0.6.7. Known limits in CHANGELOG.

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Release de entrevista **v1.0.0** con motor **0.6.7**. Pytest y build web en verde.
Quedan documentados los límites conocidos: half-hot del plan 3, receptáculo del
water heater en plan 4, y millwork que a veces se traza como cable. Motor y app
congelados; nadie cambia comportamiento sin tu OK.
