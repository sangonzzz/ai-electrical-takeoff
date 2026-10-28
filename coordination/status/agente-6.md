# Agente 6 — Frontend (web/)

## Estado

v1.0.5 polish: un solo clear en search; sin em dashes en copy de UI.

## Hecho

- `palette-search` → `type="text"` (sin clear nativo del browser)
- Em dashes de frases de usuario → punto/coma/dos puntos
- `package.json` → `1.0.5`
- v1.0.4: search, Atreyus mark, version chips

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm build
```

## Siguiente

- Agente 1 tag v1.0.5

## Bloqueos

- Ninguno

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Quité la doble X del buscador de Components y reemplacé los guiones largos de las
frases visibles por puntos o dos puntos. App queda en v1.0.5.
