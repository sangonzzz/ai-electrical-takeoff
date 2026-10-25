"""Sheet analysis orchestration (owned by Agente 2)."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.models import SheetResult


def analyze_sheet(
    pdf_path: str | Path,
    page_index: int,
    *,
    use_llm: bool = True,
    with_bom: bool = True,
) -> SheetResult:
    """Run the full per-sheet pipeline and return a SheetResult.

    Steps: pdf_context -> viewport -> legend -> symbols -> classify ->
    (optional LLM adjudication) -> rooms -> (optional BOM) -> SheetResult.
    """
    raise NotImplementedError("Agente 2: implement analyze_sheet")
