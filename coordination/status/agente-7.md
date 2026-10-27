# Agente 7 — Evaluation, overlay, CI checks

## Estado

E2E re-run after A5/A6 undo/redo: **all steps pass** (including `undo_then_redo`).
Plan overlays regenerated: **pass** (plans 1–4 PNG + `overlays.pdf`).

## Hecho

- Re-ran Playwright vs docker (API image rebuilt so `/restore` + `/history` exist).
- `undo_then_redo` now hard-fails the suite if undo/redo break; waits for network.
- Re-ran `uv run takeoff eval --results-dir out --out eval/reports` → overlays refreshed.
- Acked A5/A6 undo-ready messages by verifying green e2e.

## E2E step results (2026-10-26, after `docker compose build api`)

| step | status | notes |
|------|--------|-------|
| home | **pass** | |
| load_demo | **pass** | |
| sheets_succeed | **pass** | |
| open_plan1 | **pass** | |
| marks_visible | **pass** | |
| takeoff_highlight | **pass** | |
| select_details | **pass** | |
| change_subtype | **pass** | |
| drag_room | **pass** | |
| delete_decrements | **pass** | |
| add_click_palette | **pass** | |
| add_drag_palette | **pass** | |
| undo_then_redo | **pass** | client stack + restore API |
| edit_xy | **pass** | |
| download_excel | **pass** | |
| download_quote_pdf | **pass** | |
| reload_persists | **pass** | |
| bom_total | **pass** | |
| plans_2_4 | **pass** | |

Suite exit: **1 passed** (no soft-fails on undo).

## Plan overlays

| artifact | status |
|----------|--------|
| `eval/reports/plan1_overlay.png` | **pass** (marks + labels visible) |
| `eval/reports/plan2_overlay.png` | **pass** |
| `eval/reports/plan3_overlay.png` | **pass** |
| `eval/reports/plan4_overlay.png` | **pass** |
| `eval/reports/overlays.pdf` | **pass** (~875 KB) |
| `eval/reports/latest.md` | written |

Command: `uv run takeoff eval --results-dir out --out eval/reports`

## Cómo probarlo

```bash
make up   # rebuild api if undo routes 404: docker compose build api worker && docker compose up -d api worker
make e2e
uv run takeoff eval --results-dir out --out eval/reports
```

## Siguiente

- Keep e2e green on CI when Agente 1 wires it.
- Generalization title-gate still open (product/Agente 2 decision).

## Bloqueos

Ninguno.

## Decisions

- First undo fail tonight was stale API image (restore 404), not frontend — rebuild required.
- Undo step is no longer soft-fail.

## Needs from Santiago

None.

## Explicación para Santiago

Volví a correr la prueba del navegador después de que Agente 5 y 6 metieron undo/redo.
Había que **reconstruir la imagen del API** en Docker; si no, `/restore` devolvía 404 y
el Redo fallaba. Con el API nuevo, **todas las filas pasan**, incluido Undo → Redo.
También regeneré los overlays de los 4 planos (PNG + PDF) desde los JSON en `out/`;
se ven bien (marcas coloreadas sobre el plan).
