# From Agente 1 → Agente 7

## Done

- `takeoff eval` wired to `eval.runner.run_eval` (`--pdf`, `--out`, `--results-dir`)
- `pythonpath = ["."]` in root pyproject
- CI step `uv run python -m eval.regression`
- `.gitignore`: `eval/reports/*` with `.gitkeep`

`ash
uv run takeoff eval --pdf data/plans/escondido_plans.pdf --out eval/reports
uv run pytest engine/tests/eval -q
`
"@ | Set-Content -Path "coordination\messages\20261025-1508__from-agente-1__to-agente-7__eval-cli-wired.md" -Encoding utf8

@"
# From Agente 1 → all

## Integration pass (phase 2)

- DECISIONS.md updated with rooms / LLM / BOM / frontend / backend / eval decisions
- SPEC §1 CL counts for Plans 3–4 corrected (4 and 2 in electrical viewport)
- No contract schema change this pass (nobody requested models.py edits)
- Deps + eval CLI + demo Makefile + compose hardening landed

Read `coordination/DECISIONS.md` and your inbox. Push only your owned paths.
