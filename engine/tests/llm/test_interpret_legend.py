"""interpret_legend with fake transport + recorded fixture shape."""

from __future__ import annotations

import json
from pathlib import Path

from takeoff_engine.config import Settings
from takeoff_engine.llm.cache import DiskCache
from takeoff_engine.llm.client import ClaudeClient
from takeoff_engine.llm.legend import interpret_legend
from takeoff_engine.llm.schemas import LegendInterpretResponse
from takeoff_engine.models import BBox, Category, LegendEntry, LlmUsage

from .fakes import FakeTransport, tiny_png

FIXTURES = Path(__file__).parent / "fixtures"


def _settings() -> Settings:
    return Settings(
        anthropic_api_key="test-key",
        anthropic_model="claude-sonnet-5-5",
        anthropic_model_cheap="claude-haiku-5-5",
        enable_llm=True,
        enable_bom=True,
    )


def _rules_entries() -> list[LegendEntry]:
    bb = BBox(x0=0, y0=0, x1=10, y1=10)
    return [
        LegendEntry(
            id="leg-switch",
            description="SINGLE POLE SWITCH",
            codes=["D", "3D"],
            category=Category.SWITCH,
            subtype="single_pole",
            symbol_bbox=bb,
            interpreted_by="rules",
        ),
        LegendEntry(
            id="leg-fan",
            description="CEILING FAN OPTIONAL",
            codes=["J"],
            category=Category.JUNCTION_BOX,  # intentional wrong rules guess
            subtype="junction_box",
            symbol_bbox=bb,
            interpreted_by="rules",
        ),
        LegendEntry(
            id="leg-sdma",
            description="SMOKE / CO DETECTOR",
            codes=["SD/MA"],
            category=Category.DETECTOR,
            subtype="smoke",  # rules incomplete; LLM says smoke_co
            symbol_bbox=bb,
            interpreted_by="rules",
        ),
        LegendEntry(
            id="leg-cw",
            description="COLD WATER",
            codes=["CW"],
            category=None,
            subtype=None,
            symbol_bbox=bb,
            interpreted_by="rules",
        ),
    ]


def test_fixture_validates_against_schema() -> None:
    raw = json.loads((FIXTURES / "legend_response.json").read_text(encoding="utf-8"))
    raw.pop("_meta", None)
    parsed = LegendInterpretResponse.model_validate(raw)
    assert len(parsed.entries) == 4


def test_interpret_legend_merges_and_warns_on_disagreement(tmp_path: Path) -> None:
    raw = json.loads((FIXTURES / "legend_response.json").read_text(encoding="utf-8"))
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
    merged = interpret_legend(
        _rules_entries(),
        tiny_png(),
        usage=usage,
        warnings=warnings,
        client=client,
    )
    by_id = {e.id: e for e in merged}
    assert by_id["leg-fan"].category == Category.CEILING_FAN
    assert by_id["leg-fan"].subtype == "ceiling_fan"
    assert by_id["leg-fan"].interpreted_by == "llm"
    assert by_id["leg-sdma"].subtype == "smoke_co"
    assert by_id["leg-sdma"].combined is True
    assert by_id["leg-cw"].category is None
    assert any("disagreement" in w for w in warnings)
    assert usage.calls == 1


def test_interpret_legend_without_key_keeps_rules() -> None:
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
    entries = _rules_entries()
    out = interpret_legend(entries, tiny_png(), warnings=warnings, client=client)
    assert out == entries
    assert any("ANTHROPIC_API_KEY" in w for w in warnings)
