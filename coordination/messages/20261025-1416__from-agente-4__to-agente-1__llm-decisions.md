# From Agente 4 → Agente 1

Please record in `coordination/DECISIONS.md` if you agree:

1. **Vision tasks use Sonnet** (`ANTHROPIC_MODEL`, default `claude-sonnet-5-5`) for
   `interpret_legend`, `adjudicate`, and `baseline_vision_takeoff`. Cheap Haiku
   remains on `Settings` for future high-volume text-only work — not for the
   presentation baseline (fair hybrid vs LLM-alone comparison).
2. **Optional kwargs** on the three public LLM functions: `usage: LlmUsage | None`,
   `warnings: list[str] | None`, `client: ClaudeClient | None`. Required signatures
   from the scaffold are unchanged.
3. **No-key behavior**: warn + rules-only / empty adjudication / empty baseline;
   never raise for missing key.
4. **Adjudicate batching**: default 6 candidates per call; crop ~300 dpi, 18 pt pad,
   red outline. Labels = `category.subtype` from SPEC §2 or `not_a_component`.

Also: please ask Santiago for `ANTHROPIC_API_KEY` in `.env` so we can replace
hand-shaped fixtures with one real recorded Anthropic response.

Docs: `docs/modules/ai.md`. Status: `coordination/status/agente-4.md`.
