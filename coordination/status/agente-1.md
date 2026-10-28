# Agente 1 — Lead / architecture / integration

## Estado

**v1.0.4 blocked** — falta commit A6 “for Atreyus” mark (logo).

## Hecho

- Inbox A6 partial: component search + version chips OK; Atreyus mark blocked
- No tag `v1.0.4` (step 2 failed)

## Cómo probarlo

```bash
git log --oneline v1.0.3..HEAD
# need third [A6] for Atreyus mark before re-run
```

## Siguiente

- Santiago: drop `web/public/brand/atreyus-logo.svg` (or `.png`)
- A6 finishes Task 2 → A1 re-runs UI-only v1.0.4

## Bloqueos

- Official Atreyus logo missing (A6 429/403 from atreyus.ai)

## Decisions

- (ninguno)

## Needs from Santiago

- Brand logo file for Agente 6

## Explicación para Santiago

No etiqueté v1.0.4: hay búsqueda y chips, pero falta la marca “for Atreyus”
porque no está el logo oficial. Cuando lo dejes en `web/public/brand/`, A6 termina
y yo reintento el release.
