# Agente 6 — Frontend (web/)

## Estado

Búsqueda en palette + chips Engine/App/PDF listos. **Bloqueado** la marca “for Atreyus”: falta el logo oficial.

## Hecho

- Palette search: input + sinónimos + `/` / Esc / Enter (`2a32a9c`)
- Chips: `Engine 0.6.7`, `App v1.0.4` (desde `package.json`), `PDF {hash}…` (`66692ce`)
- package.json → `1.0.4`

## Bloqueos

- Logo Atreyus: `web/public/brand/atreyus-logo.svg` (o `.png`) no existe; descarga desde
  atreyus.ai devolvió 429/403. **No inventé el logo.** Necesito el archivo de Santiago.

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm build
# Palette: escribir "outlet" / "3-way" / "/"
# Header: chips Engine / App v1.0.4 / PDF …
```

## Siguiente

- Colocar logo + “for Atreyus” / “Prepared for” cuando Santiago deje el archivo
- Luego mensaje final v1.0.4 a Agente 1

## Decisions

- `__APP_VERSION__` inyectado en Vite desde `package.json`

## Needs from Santiago

- Archivo oficial del logo en `web/public/brand/atreyus-logo.svg` o `.png` (sin redibujar)

## Explicación para Santiago

Ya hay búsqueda en Components y chips claros de versión en el header. Para el sello
“for Atreyus” necesito el logo real: atreyus.ai no dejó descargarlo. Déjalo en
`web/public/brand/` y termino esa parte + el mensaje de v1.0.4.
