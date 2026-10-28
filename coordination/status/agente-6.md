# Agente 6 — Frontend (web/)

## Estado

v1.0.6 listo: Home guarda todos los documentos (lista en localStorage).

## Hecho

- Lista `takeoff.documents` en localStorage (orden de inserción, sin duplicados)
- Migración de `sessionStorage` `takeoff.documentId`; fallback en memoria si storage falla
- Demo primero (“Escondido demo”); uploads debajo; un solo heading **Sheets**
- Grupo por documento con poll de `GET /documents/{id}`; 404 se saca de la lista
- Menú ⋯ → **Remove from list** (confirmación inline; no borra en DB)
- Vitest `documentList.test.ts`; `package.json` → `1.0.6`

## Cómo probarlo

```bash
cd web
pnpm exec tsc --noEmit && pnpm exec vitest run && pnpm build
```

## Siguiente

- Agente 1 tag / release notes v1.0.6

## Bloqueos

- Ninguno

## Decisions

- Ids de demo recordados en `takeoff.demoDocumentId` para título y orden
- Remove solo toca la lista local; no hay DELETE al API

## Needs from Santiago

- (ninguno)

## Explicación para Santiago

La home ya no reemplaza el documento anterior: guarda una lista de ids en el
navegador. El demo de Escondido queda arriba; cada PDF que subas aparece debajo
con sus hojas. El menú ⋯ solo oculta el documento de la lista; el análisis sigue
en la base de datos. App v1.0.6.
