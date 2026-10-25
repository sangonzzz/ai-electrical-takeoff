# From Agente 4 → Agente 2

## LLM layer usable

`interpret_legend` and `adjudicate` are implemented and tested offline.

### How to call

```python
from takeoff_engine.llm import interpret_legend, adjudicate
from takeoff_engine.models import LlmUsage

usage = LlmUsage()
warnings: list[str] = []

# After your rule-based legend + a PNG crop of the legend region:
legend = interpret_legend(entries, legend_png_bytes, usage=usage, warnings=warnings)

# For needs_review candidates (geometry already found WHERE):
adjs = adjudicate(
    pdf_path, page_index, review_candidates, legend,
    usage=usage, warnings=warnings,
)
# each Adjudication: candidate_id, label ("category.subtype" | "not_a_component"),
# confidence, reason — never coordinates
```

### Contract notes

- Optional kwargs `usage` / `warnings` / `client` — required args unchanged.
- No API key / `ENABLE_LLM=false`: `interpret_legend` returns rules entries as-is;
  `adjudicate` returns `[]`; both append a warning.
- Legend merge: LLM refines your rules; disagreements → `warnings`.
- Adjudicate renders its own crops (~300 dpi, red outline) from `candidate.bbox`.
  Legend thumbnails use each entry’s `symbol_bbox` — please keep those accurate.
- Fold `usage` into `SheetResult.llm_usage` and `warnings` into `SheetResult.warnings`.

### Prompts

`engine/prompts/legend_v1.md`, `adjudicate_v1.md`. Prompt versions:
`PROMPT_LEGEND`, `PROMPT_ADJUDICATE` from `takeoff_engine.llm`.

### Tests

`uv run pytest engine/tests/llm -v` (22 passed, fake transport, no network).
