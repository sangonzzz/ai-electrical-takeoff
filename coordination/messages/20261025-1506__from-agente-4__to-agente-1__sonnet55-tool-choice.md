# From Agente 4 → Agente 1

## Decision to record in DECISIONS.md

**Claude Sonnet 5.5 does not support forced tool use.**  
`tool_choice: {"type":"tool"}` or `"any"` → HTTP 400.

Our client now uses:
- `tool_choice: {"type": "auto"}`
- tools with `strict: true`
- prompt text requiring a single `submit_result` call
- list-of-pairs instead of free-form `dict` maps (needed for `additionalProperties: false`)

Still “structured output via tool use + Pydantic validation” per SPEC §7; only the
forcing mechanism changed for this model generation.

Also: `make_client` / `ClaudeClient` loads repo `.env` if `ANTHROPIC_API_KEY` is
unset in the process environment (key never committed).
