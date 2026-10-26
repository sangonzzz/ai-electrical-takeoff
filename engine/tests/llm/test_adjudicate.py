"""adjudicate with fake transport; crops rendered from the Escondido PDF."""

from __future__ import annotations

import json
from pathlib import Path

from takeoff_engine.config import Settings
from takeoff_engine.llm.adjudicate_task import adjudicate
from takeoff_engine.llm.cache import DiskCache
from takeoff_engine.llm.client import ClaudeClient
from takeoff_engine.llm.crops import render_candidate_crop
from takeoff_engine.llm.schemas import AdjudicateResponse
from takeoff_engine.models import BBox, Category, LegendEntry, LlmUsage
from takeoff_engine.types import Candidate

from .fakes import FakeTransport

FIXTURES = Path(__file__).parent / "fixtures"


def _settings() -> Settings:
    return Settings(
        anthropic_api_key="test-key",
        anthropic_model="claude-sonnet-5-5",
        anthropic_model_cheap="claude-haiku-5-5",
        enable_llm=True,
        enable_bom=True,
    )


def test_fixture_validates() -> None:
    raw = json.loads((FIXTURES / "adjudicate_response.json").read_text(encoding="utf-8"))
    raw.pop("_meta", None)
    parsed = AdjudicateResponse.model_validate(raw)
    assert len(parsed.items) == 3
    assert all("x" not in it.reason.lower() or "box" not in it.reason.lower() for it in parsed.items)


def test_render_candidate_crop_png(plans_pdf: Path, tmp_path: Path) -> None:
    cand = Candidate(
        id="cand-1",
        bbox=(1100.0, 400.0, 1120.0, 420.0),
        center=(1110.0, 410.0),
        segment_ids=[],
        fill_ids=[],
    )
    png = render_candidate_crop(plans_pdf, 0, cand)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    debug = tmp_path / "crop_cand1.png"
    debug.write_bytes(png)
    # Also write under out/debug when possible for visual inspection
    out_debug = Path(__file__).resolve().parents[3] / "out" / "debug"
    out_debug.mkdir(parents=True, exist_ok=True)
    (out_debug / "llm_crop_cand1.png").write_bytes(png)


def test_adjudicate_batch_with_fixture(plans_pdf: Path, tmp_path: Path) -> None:
    raw = json.loads((FIXTURES / "adjudicate_response.json").read_text(encoding="utf-8"))
    raw.pop("_meta", None)
    transport = FakeTransport([raw])
    usage = LlmUsage()
    warnings: list[str] = []
    client = ClaudeClient(
        settings=_settings(),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=usage,
    )
    candidates = [
        Candidate("cand-1", (1100, 400, 1120, 420), (1110, 410), [], []),
        Candidate("cand-2", (1200, 450, 1250, 460), (1225, 455), [], []),
        Candidate("cand-3", (1000, 300, 1060, 360), (1030, 330), [], []),
    ]
    legend = [
        LegendEntry(
            id="leg-1",
            description="CEILING FAN",
            codes=["J"],
            category=Category.CEILING_FAN,
            subtype="ceiling_fan",
            symbol_bbox=BBox(x0=1460, y0=80, x1=1490, y1=110),
            interpreted_by="rules",
        )
    ]
    results = adjudicate(
        plans_pdf,
        0,
        candidates,
        legend,
        usage=usage,
        warnings=warnings,
        client=client,
    )
    assert {r.candidate_id for r in results} == {"cand-1", "cand-2", "cand-3"}
    by_id = {r.candidate_id: r for r in results}
    assert by_id["cand-2"].label == "not_a_component"
    assert by_id["cand-3"].label == "ceiling_fan.ceiling_fan"
    assert usage.calls == 1
    # Ensure request included images (legend thumb + crops)
    assert any(
        block.get("type") == "image"
        for msg in transport.calls[0]["messages"]
        if msg["role"] == "user"
        for block in msg["content"]
        if isinstance(block, dict)
    )


def test_adjudicate_one_call_for_many_candidates(plans_pdf: Path, tmp_path: Path) -> None:
    """Default batch size covers a full sheet in one API call."""
    from takeoff_engine.llm.adjudicate_task import DEFAULT_BATCH_SIZE

    assert DEFAULT_BATCH_SIZE >= 1000
    raw = json.loads((FIXTURES / "adjudicate_response.json").read_text(encoding="utf-8"))
    raw.pop("_meta", None)
    # Expand fixture items to match 8 candidates (same labels cycling)
    base_items = list(raw["items"])
    candidates = [
        Candidate(f"cand-{i}", (1100 + i, 400, 1120 + i, 420), (1110 + i, 410), [], [])
        for i in range(8)
    ]
    raw["items"] = [
        {
            "candidate_id": c.id,
            "label": base_items[i % len(base_items)]["label"],
            "confidence": 0.8,
            "reason": "batch test",
        }
        for i, c in enumerate(candidates)
    ]
    transport = FakeTransport([raw])
    client = ClaudeClient(
        settings=_settings(),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=LlmUsage(),
    )
    results = adjudicate(
        plans_pdf,
        0,
        candidates,
        [],
        client=client,
    )
    assert len(transport.calls) == 1
    assert len(results) == 8


def test_adjudicate_without_key(plans_pdf: Path) -> None:
    client = ClaudeClient(
        settings=Settings(
            anthropic_api_key=None,
            anthropic_model="claude-sonnet-5-5",
            anthropic_model_cheap="claude-haiku-5-5",
            enable_llm=True,
            enable_bom=True,
        ),
        transport=None,
    )
    warnings: list[str] = []
    out = adjudicate(
        plans_pdf,
        0,
        [Candidate("c", (1, 1, 2, 2), (1.5, 1.5), [], [])],
        [],
        warnings=warnings,
        client=client,
    )
    assert out == []
    assert warnings
