# Agente 6 — Frontend (web/)

## Estado

v1.0.4 UI completo: búsqueda, marca Atreyus, chips de versión.

## Hecho

- Component search (`2a32a9c`)
- Version chips Engine / App v1.0.4 / PDF (`66692ce`)
- for Atreyus: logo byte-for-byte en `web/public/brand/atreyus-logo.png`; header + home

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm build
```

## Siguiente

- Agente 1 tag v1.0.4

## Bloqueos

- Ninguno

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

Las tres piezas de v1.0.4 están: buscar en Components, sello “for Atreyus” con tu
logo oficial, y chips Engine / App / PDF. Listo para el tag de Agente 1 (sin push).
