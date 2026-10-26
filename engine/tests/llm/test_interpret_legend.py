"""interpret_legend with fake transport + recorded fixture shape."""

from __future__ import annotations

import json
from pathlib import Path

from takeoff_engine.config import Settings
from takeoff_engine.llm.cache import DiskCache
from takeoff_engine.llm.client import ClaudeClient
from takeoff_engine.llm.ids import stable_legend_id
from takeoff_engine.llm.legend import interpret_legend
from takeoff_engine.llm.schemas import LegendInterpretResponse
from takeoff_engine.models import BBox, Category, LegendEntry, LlmUsage

from .fakes import FakeTransport, tiny_png


def _fixture_with_stable_ids(entries: list[LegendEntry], raw: dict) -> dict:
    """Rewrite fixture entry_ids to match stable prompt ids."""
    by_desc = {e.description: e for e in entries}
    out_entries = []
    for item in raw["entries"]:
        # Match synthetic fixture ids via description keywords in our rules fixtures
        entry = None
        for e in entries:
            if item["entry_id"].replace("leg-", "") in e.id or item["entry_id"] == e.id:
                entry = e
                break
        if entry is None:
            # Fall back: map by order for our 4-row synthetic fixture
            idx = len(out_entries)
            entry = entries[idx] if idx < len(entries) else entries[0]
        sid = stable_legend_id(
            entry.description,
            entry.codes,
            (
                entry.symbol_bbox.x0,
                entry.symbol_bbox.y0,
                entry.symbol_bbox.x1,
                entry.symbol_bbox.y1,
            ),
        )
        cloned = dict(item)
        cloned["entry_id"] = sid
        out_entries.append(cloned)
        _ = by_desc  # silence lint
    return {"entries": out_entries}

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


def test_recorded_anthropic_fixture_validates() -> None:
    """Real Claude response from Escondido Plan 1 (no network in CI)."""
    path = FIXTURES / "legend_response.recorded.json"
    assert path.is_file(), "missing recorded fixture — re-run with ANTHROPIC_API_KEY"
    raw = json.loads(path.read_text(encoding="utf-8"))
    meta = raw.pop("_meta", {})
    parsed = LegendInterpretResponse.model_validate(raw)
    assert len(parsed.entries) >= 20
    assert meta.get("model") == "claude-sonnet-5-5"
    assert meta.get("prompt_version") == "legend_v1"
    for item in parsed.entries:
        low = item.reason.lower()
        assert "bbox" not in low
        assert "coordinate" not in low
        assert "pixel" not in low


def test_interpret_legend_uses_cheap_model(tmp_path: Path) -> None:
    entries = _rules_entries()
    raw = json.loads((FIXTURES / "legend_response.json").read_text(encoding="utf-8"))
    raw.pop("_meta", None)
    transport = FakeTransport([_fixture_with_stable_ids(entries, raw)])
    client = ClaudeClient(
        settings=_settings(),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=LlmUsage(),
    )
    interpret_legend(entries, tiny_png(), client=client)
    assert transport.calls[0]["model"] == "claude-haiku-5-5"


def test_interpret_legend_merges_and_warns_on_disagreement(tmp_path: Path) -> None:
    entries = _rules_entries()
    raw = json.loads((FIXTURES / "legend_response.json").read_text(encoding="utf-8"))
    raw.pop("_meta", None)
    transport = FakeTransport([_fixture_with_stable_ids(entries, raw)])
    usage = LlmUsage()
    warnings: list[str] = []
    client = ClaudeClient(
        settings=_settings(),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=usage,
    )
    merged = interpret_legend(
        entries,
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
