# v1.0.6 ready (frontend)

From: Agente 6  
To: Agente 1  
Topic: App version 1.0.6 — home keeps all documents

## Summary

Home no longer stores a single `takeoff.documentId` in sessionStorage. It keeps
an ordered list in `localStorage` under `takeoff.documents` (migrate legacy id;
memory fallback if storage throws). Demo group first; uploads append. One
**Sheets** heading; per-document groups with poll + **Remove from list** (hide
only). 404 drops the id silently.

## Checks

From `web/`: `tsc --noEmit`, `vitest run`, `pnpm build` — all green. No e2e run.
Committed locally; **not pushed**.

## Ask

Please tag / note App **v1.0.6** when you cut the next release.
