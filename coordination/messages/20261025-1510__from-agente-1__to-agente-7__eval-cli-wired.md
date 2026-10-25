# From Agente 1 → Agente 7

## Done

- `takeoff eval` wired to `eval.runner.run_eval` (`--pdf`, `--out`, `--results-dir`)
- `pythonpath = ["."]` in root pyproject
- CI step `uv run python -m eval.regression`
- `.gitignore`: `eval/reports/*` with `.gitkeep`

```bash
uv run takeoff eval --pdf data/plans/escondido_plans.pdf --out eval/reports
uv run pytest engine/tests/eval -q
```
