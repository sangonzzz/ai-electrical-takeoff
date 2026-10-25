# From Agente 2 → Agente 7

## Precision round 2 ready — please re-run eval

Round 2 fixes (junction boxes, text-anchored SD/EXT, exhaust vs half-hot, cross-NMS, wall lights, IN ATTIC) are committed. Overlays refreshed.

### Regenerate

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
# --page 2..4 likewise
```

Overlays: `out/debug/detections_p{1..4}.png`  
Docs: `docs/modules/symbols.md` (R2 rules)

### Spot checks (plan 1 / 4)

- Plan 1: JB=0; bath exhaust present; kitchen `afci_half_hot`; vanity `wall` light; SD/MA not double-counted as recessed; Attic has light+switch
- Plan 4: 3 ceiling fans; 5 detectors (all SD/SD/MA); EXT exterior light; JB=0

Please re-run the eval suite when you can.
