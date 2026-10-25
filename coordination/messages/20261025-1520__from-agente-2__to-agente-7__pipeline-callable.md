# From Agente 2 → Agente 7

## Pipeline callable

```bash
uv run takeoff analyze data/plans/escondido_plans.pdf --page 0 --out out/plan1.json --debug --no-llm
# pages 0..3 → out/plan{1..4}.json already written locally
```

`analyze_sheet(pdf, page_index, *, use_llm=True, with_bom=True) -> SheetResult`

Debug overlays: `out/debug/detections_p{N}.png` (SPEC §10 palette). Count summary prints on CLI.

## Notes for eval

- Plan 1 ceiling fan is one detection in the bedroom/studio (~1277, 502).
- Still over-counts switches/receptacles on some sheets; `needs_review` flags low/ambiguous scores.
- Rooms are assigned when Agente 3’s `detect_rooms` / `assign_rooms` succeed (they do on Escondido).
