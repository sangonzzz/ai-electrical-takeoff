# Module: models

Owner: Agente 1. Frozen contracts — changes require Agente 1 + regenerated schema/TS.

## What it does

Pydantic v2 models for `SheetResult`, `Detection`, `Room`, `Takeoff`, `Bom`, etc.
`SUBTYPES` mirrors SPEC section 2. `Detection` validates that `subtype` belongs
to `category`.

## Schema export

```bash
uv run takeoff schema
npx json-schema-to-typescript contracts/schema.json -o web/src/types/contracts.ts
```
