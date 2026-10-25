"""baseline_vision_takeoff — LLM-only counts (eval baseline)."""

from __future__ import annotations

import json
from pathlib import Path

from takeoff_engine.config import Settings
from takeoff_engine.llm.baseline import baseline_vision_takeoff
from takeoff_engine.llm.cache import DiskCache
from takeoff_engine.llm.client import ClaudeClient
from takeoff_engine.llm.schemas import BaselineVisionResponse
from takeoff_engine.models import LlmUsage

from .fakes import FakeTransport, tiny_png

FIXTURES = Path(__file__).parent / "fixtures"


def test_fixture_validates() -> None:
    raw = json.loads((FIXTURES / "baseline_response.json").read_text(encoding="utf-8"))
    raw.pop("_meta", None)
    parsed = BaselineVisionResponse.model_validate(raw)
    assert len(parsed.rooms) == 2


def test_baseline_maps_rooms(tmp_path: Path) -> None:
    raw = json.loads((FIXTURES / "baseline_response.json").read_text(encoding="utf-8"))
    raw.pop("_meta", None)
    transport = FakeTransport([raw])
    usage = LlmUsage()
    client = ClaudeClient(
        settings=Settings(
            anthropic_api_key="test-key",
            anthropic_model="claude-sonnet-5-5",
            anthropic_model_cheap="claude-haiku-5-5",
            enable_llm=True,
            enable_bom=True,
        ),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=usage,
    )
    warnings: list[str] = []
    counts = baseline_vision_takeoff(
        tiny_png(),
        ["LIVING", "BATH", "KITCHEN"],
        usage=usage,
        warnings=warnings,
        client=client,
    )
    assert counts["LIVING"]["ceiling_fan.ceiling_fan"] == 1
    assert counts["BATH"]["exhaust_fan.bath_exhaust"] == 1
    assert counts["KITCHEN"] == {}
    assert any("missing room_name" in w for w in warnings)
    assert usage.calls == 1


def test_baseline_without_key() -> None:
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
    out = baseline_vision_takeoff(tiny_png(), ["LIVING"], warnings=warnings, client=client)
    assert out == {"LIVING": {}}
    assert warnings
