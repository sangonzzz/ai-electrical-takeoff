"""CLI entry point: ``takeoff analyze | eval | schema``.

Agente 1 owns the skeleton. Agente 2 fills in analyze (via pipeline);
Agente 7 owns eval. Schema export stays with Agente 1 (contracts owner).
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from takeoff_engine.models import (
    SCHEMA_VERSION,
    BBox,
    Bom,
    BomLine,
    Box,
    Category,
    Detection,
    Evidence,
    LegendEntry,
    LlmUsage,
    Point,
    Room,
    Sheet,
    SheetImage,
    SheetResult,
    Takeoff,
    TakeoffRow,
    WireRun,
)

app = typer.Typer(
    name="takeoff",
    help="AI electrical plan takeoff CLI",
    no_args_is_help=True,
)


@app.command("analyze")
def analyze_cmd(
    pdf: Path = typer.Argument(..., exists=True, help="Path to the plans PDF"),  # noqa: B008
    page: int = typer.Option(0, "--page", "-p", help="0-based page index"),
    out: Path = typer.Option(Path("out/sheet_result.json"), "--out", "-o"),  # noqa: B008
    debug: bool = typer.Option(False, "--debug", help="Write debug PNGs to out/debug/"),
    use_llm: bool = typer.Option(True, "--llm/--no-llm"),
    with_bom: bool = typer.Option(True, "--bom/--no-bom"),
) -> None:
    """Analyze one sheet and write SheetResult JSON."""
    from collections import Counter

    from takeoff_engine.pipeline import analyze_sheet, write_debug_overlay

    result = analyze_sheet(pdf, page, use_llm=use_llm, with_bom=with_bom)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Wrote {out}")
    counts = Counter(d.category.value for d in result.detections)
    typer.echo(f"detections={len(result.detections)} by_category={dict(counts)}")
    if result.warnings:
        typer.echo(f"warnings={len(result.warnings)}")
    if debug:
        debug_dir = Path("out/debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        overlay = debug_dir / f"detections_p{page + 1}.png"
        write_debug_overlay(pdf, page, result, overlay)
        typer.echo(f"Debug overlay: {overlay}")


@app.command("eval")
def eval_cmd(
    pdf: Path | None = typer.Option(None, "--pdf", help="Plans PDF"),  # noqa: B008
    out: Path = typer.Option(Path("eval/reports"), "--out", "-o"),  # noqa: B008
    results_dir: Path | None = typer.Option(  # noqa: B008
        None, "--results-dir", help="Dir with plan1.json… SheetResult files"
    ),
) -> None:
    """Run evaluation against ground truth (owned by Agente 7)."""
    import sys

    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from eval.runner import run_eval

    run_eval(pdf=pdf, out_dir=out, results_dir=results_dir)
    typer.echo(f"Wrote reports under {out}")


@app.command("schema")
def schema_cmd(
    out: Path = typer.Option(  # noqa: B008
        Path("contracts/schema.json"),
        "--out",
        "-o",
        help="Output JSON Schema path",
    ),
) -> None:
    """Export Pydantic contracts as JSON Schema to contracts/schema.json."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/sangonzzz/ai-electrical-takeoff/contracts/schema.json",
        "title": "AI Electrical Takeoff Contracts",
        "description": f"Schema version {SCHEMA_VERSION}",
        "$defs": {
            "Point": Point.model_json_schema(),
            "BBox": BBox.model_json_schema(),
            "Evidence": Evidence.model_json_schema(),
            "Detection": Detection.model_json_schema(),
            "Room": Room.model_json_schema(),
            "LegendEntry": LegendEntry.model_json_schema(),
            "WireRun": WireRun.model_json_schema(),
            "Box": Box.model_json_schema(),
            "SheetImage": SheetImage.model_json_schema(),
            "Sheet": Sheet.model_json_schema(),
            "LlmUsage": LlmUsage.model_json_schema(),
            "SheetResult": SheetResult.model_json_schema(),
            "TakeoffRow": TakeoffRow.model_json_schema(),
            "Takeoff": Takeoff.model_json_schema(),
            "BomLine": BomLine.model_json_schema(),
            "Bom": Bom.model_json_schema(),
            "Category": {"type": "string", "enum": [c.value for c in Category]},
        },
        "oneOf": [
            {"$ref": "#/$defs/SheetResult"},
            {"$ref": "#/$defs/Takeoff"},
            {"$ref": "#/$defs/Bom"},
        ],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    typer.echo(f"Wrote {out}")


if __name__ == "__main__":
    app()
