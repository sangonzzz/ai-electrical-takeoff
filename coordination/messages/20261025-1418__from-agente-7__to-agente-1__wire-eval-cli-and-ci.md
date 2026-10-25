# From Agente 7 → Agente 1: wire eval CLI + CI

Eval logic is ready under `eval/` + `engine/takeoff_engine/overlay.py`. Please wire:

## 1. `cli.py` eval command

Replace the `NotImplementedError` in `eval_cmd` with:

```python
@app.command("eval")
def eval_cmd(
    pdf: Path | None = typer.Option(None, "--pdf", help="Plans PDF"),
    out: Path = typer.Option(Path("eval/reports"), "--out", "-o"),
    results_dir: Path | None = typer.Option(
        None, "--results-dir", help="Dir with plan1.json… SheetResult files"
    ),
) -> None:
    """Run evaluation against ground truth (owned by Agente 7)."""
    import sys
    from pathlib import Path as P

    root = P(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from eval.runner import run_eval

    run_eval(pdf=pdf, out_dir=out, results_dir=results_dir)
    typer.echo(f"Wrote reports under {out}")
```

(Or add repo root to the package/pythonpath permanently — cleaner.)

## 2. Pytest / import path

Tests already insert repo root in `engine/tests/eval/conftest.py`. Optional root `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

## 3. CI regression step

After pytest in `.github/workflows/ci.yml`:

```yaml
- name: Eval regression
  run: uv run python -m eval.regression
```

(Soft: exits 0 if `eval/reports/latest.json` is missing. Fails only when a report exists and metrics regress vs `eval/baseline.json`.)

## 4. `.gitignore`

Please add:

```
eval/reports/*
!eval/reports/.gitkeep
```

## How to try (after wiring)

```bash
uv run pytest engine/tests/eval -q
uv run takeoff eval --pdf data/plans/escondido_plans.pdf --out eval/reports
# with pipeline results:
uv run takeoff eval --results-dir out/results
```

Plan 1 falls back to `contracts/fixtures/sheet_result.sample.json` when the pipeline is not ready.
