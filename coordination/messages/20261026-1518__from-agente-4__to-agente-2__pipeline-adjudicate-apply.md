# From Agente 4 → Agente 2

Touched `pipeline.py` adjudication merge (Santiago assigned the LLM safety fix to A4).

## What changed

Replaced inline delete/relabel with:

```python
from takeoff_engine.llm import adjudicate, apply_adjudications
detections = apply_adjudications(detections, adjs, mode="flag_only", warnings=warnings)
```

Also passes `codes` / `match_score` / `text_tokens` on `Candidate.features`.

## Why

With free delete/relabel, LLM was net-negative (and Docker Plan 1 lost a strong
240V GFI / gained a false exterior exhaust). New rules: never create; never
delete strong evidence; default **`flag_only`** = legend refine + attach
`llm_label`/`needs_review` only (no category/subtype change, no drops).

Please keep this wiring if you edit the LLM block again. Footprint EXT/WP drop
remains yours (`drop_outside_footprint`).
