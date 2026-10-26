# From Agente 1 → Agente 6

## Fixture import in Docker

Compose now mounts `./contracts:/contracts:ro` so
`web/src/api/fixture.ts`'s `../../../contracts/fixtures/sheet_result.sample.json`
resolves inside the web container (`/app/src/api` → `/contracts`).

## Please (production hygiene)

Make the fixture import **lazy**: dynamic `import()` only when
`VITE_USE_FIXTURE=true`, so production / API mode never depends on `contracts/`
at build or startup. Static top-level import of the JSON forces Vite to resolve
it even when fixture mode is off.
