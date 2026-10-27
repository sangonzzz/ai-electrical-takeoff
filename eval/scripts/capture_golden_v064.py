"""Capture normalized golden SheetResults from a v0.6.4-stable engine tree.

Usage (from repo root, after ``git worktree add <tmp> v0.6.4-stable``)::

    set ENGINE_ROOT=%TEMP%\\takeoff-wt-v064-stable
    .\\.venv\\Scripts\\python.exe eval/scripts/capture_golden_v064.py

Writes ``eval/golden/v0.6.4/plan{1..4}.json``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENGINE_ROOT = Path(os.environ.get("ENGINE_ROOT", REPO))


def main() -> int:
    engine_path = ENGINE_ROOT / "engine"
    if not (engine_path / "takeoff_engine").is_dir():
        print(f"ENGINE_ROOT missing takeoff_engine: {engine_path}", file=sys.stderr)
        return 1

    # Prefer the tagged engine on sys.path before the installed package.
    sys.path.insert(0, str(engine_path))
    # eval package from current repo
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    from takeoff_engine.pipeline import analyze_sheet  # noqa: WPS433

    from eval.golden_normalize import (  # noqa: WPS433
        DEFAULT_PDF,
        GOLDEN_DIR,
        dump_golden,
        normalize_sheet_result,
    )

    pdf = Path(os.environ.get("GOLDEN_PDF", DEFAULT_PDF))
    if not pdf.is_file():
        print(f"PDF missing: {pdf}", file=sys.stderr)
        return 1

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    print(f"engine={engine_path}")
    print(f"pdf={pdf}")
    print(f"out={GOLDEN_DIR}")

    for plan in range(1, 5):
        page_index = plan - 1
        print(f"analyze plan{plan} (page_index={page_index}) …", flush=True)
        result = analyze_sheet(pdf, page_index, use_llm=False, with_bom=True)
        fp = normalize_sheet_result(result)
        out = GOLDEN_DIR / f"plan{plan}.json"
        dump_golden(out, fp)
        print(
            f"  wrote {out.name}: "
            f"dets={len(fp['detections'])} rooms={len(fp['rooms'])} "
            f"wires={len(fp['wire_runs'])} boxes={len(fp['boxes'])}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
