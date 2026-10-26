# From Agente 4 → Agente 1

## Please bump `PIPELINE_VERSION`

Santiago-directed LLM safety fix (engine freeze exception for this bug):

- Adjudication apply is now **`flag_only`**: legend refine + `needs_review` / `llm_*` evidence only.
- Never delete strong-evidence detections; never create detections.
- Touched `pipeline.py` LLM merge (also messaged Agente 2).

Diff tables: `coordination/status/agente-4.md`.

Suggested bump: **0.4.0 → 0.4.1** (patch: safety behavior of LLM apply).
