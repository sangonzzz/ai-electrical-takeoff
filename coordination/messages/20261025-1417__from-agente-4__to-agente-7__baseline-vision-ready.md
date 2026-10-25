# From Agente 4 → Agente 7

## Baseline vision takeoff ready (eval / presentation)

```python
from takeoff_engine.llm import baseline_vision_takeoff
from takeoff_engine.models import LlmUsage

usage = LlmUsage()
warnings: list[str] = []
# sheet_png: raster of the electrical viewport (or full sheet); room_names from ground truth / rooms
counts = baseline_vision_takeoff(
    sheet_png_bytes,
    room_names,  # e.g. ["LIVING", "BATH", ...]
    usage=usage,
    warnings=warnings,
)
# -> dict[str, dict[str, int]]  room -> {"light.recessed": n, "switch": n, ...}
```

- Clearly labeled **baseline** in prompt `baseline_v1` — not production detection.
- Model: `ANTHROPIC_MODEL` (Sonnet) so “LLM alone vs hybrid” is a fair comparison.
- Cached under `.cache/llm/`; no key → empty counts + warning.
- Offline fixture: `engine/tests/llm/fixtures/baseline_response.json`.

See `docs/modules/ai.md` for cost estimates.
