"""ClaudeClient: structured tool use, validation retry, transport retry, cache."""

from __future__ import annotations

from pathlib import Path

import anthropic
import pytest
from pydantic import BaseModel, Field

from takeoff_engine.config import Settings
from takeoff_engine.llm.cache import DiskCache
from takeoff_engine.llm.client import ClaudeClient
from takeoff_engine.models import LlmUsage

from .fakes import FakeTransport, tiny_png


class _TinyOut(BaseModel):
    label: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)


def _settings(**kwargs: object) -> Settings:
    base = dict(
        anthropic_api_key="test-key",
        anthropic_model="claude-sonnet-5-5",
        anthropic_model_cheap="claude-haiku-5-5",
        enable_llm=True,
        enable_bom=True,
    )
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


def test_call_structured_validates_and_records_usage(tmp_path: Path) -> None:
    transport = FakeTransport([{"label": "switch.dimmer", "score": 0.7}])
    usage = LlmUsage()
    client = ClaudeClient(
        settings=_settings(),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=usage,
    )
    out = client.call_structured(
        model="claude-sonnet-5-5",
        prompt_version="test_v1",
        system="sys",
        user_text="user",
        response_model=_TinyOut,
        images=[tiny_png()],
    )
    assert out.label == "switch.dimmer"
    assert usage.calls == 1
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.cost_usd > 0
    assert usage.cache_hits == 0
    assert len(transport.calls) == 1
    assert transport.calls[0]["tools"][0]["name"] == "submit_result"


def test_cache_hit_skips_transport(tmp_path: Path) -> None:
    transport = FakeTransport([{"label": "light.pendant", "score": 0.5}])
    usage = LlmUsage()
    client = ClaudeClient(
        settings=_settings(),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=usage,
    )
    kwargs = dict(
        model="claude-sonnet-5-5",
        prompt_version="test_v1",
        system="sys",
        user_text="same",
        response_model=_TinyOut,
        images=[tiny_png()],
    )
    a = client.call_structured(**kwargs)  # type: ignore[arg-type]
    b = client.call_structured(**kwargs)  # type: ignore[arg-type]
    assert a == b
    assert len(transport.calls) == 1
    assert usage.calls == 1
    assert usage.cache_hits == 1


def test_validation_error_retries_once(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            {"label": "", "score": 0.5},  # invalid: min_length
            {"label": "ok", "score": 0.9},
        ]
    )
    client = ClaudeClient(
        settings=_settings(),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=LlmUsage(),
    )
    out = client.call_structured(
        model="claude-sonnet-5-5",
        prompt_version="test_v1",
        system="sys",
        user_text="user",
        response_model=_TinyOut,
    )
    assert out.label == "ok"
    assert len(transport.calls) == 2
    # Second user message should mention validation
    second_msgs = transport.calls[1]["messages"]
    assert any(
        isinstance(m.get("content"), str) and "validation" in m["content"].lower()
        for m in second_msgs
        if m.get("role") == "user" and isinstance(m.get("content"), str)
    )


def test_transport_retries_on_429(tmp_path: Path) -> None:
    sleeps: list[float] = []

    class _Req:
        method = "POST"
        url = "https://api.anthropic.com/v1/messages"

    class _Resp:
        status_code = 429
        headers: dict[str, str] = {}
        request = _Req()

    exc = anthropic.APIStatusError(
        message="rate limited",
        response=_Resp(),  # type: ignore[arg-type]
        body=None,
    )
    transport = FakeTransport(
        [{"label": "ok", "score": 1.0}],
        fail_times=2,
        fail_exc=exc,
    )
    client = ClaudeClient(
        settings=_settings(),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=LlmUsage(),
        sleep=sleeps.append,
    )
    out = client.call_structured(
        model="claude-sonnet-5-5",
        prompt_version="test_v1",
        system="s",
        user_text="u",
        response_model=_TinyOut,
    )

    assert out.label == "ok"
    assert len(transport.calls) == 3
    assert len(sleeps) == 2


def test_non_retryable_error_raises(tmp_path: Path) -> None:
    class _Resp:
        status_code = 400
        headers: dict[str, str] = {}
        request = None

    exc = anthropic.APIStatusError(
        message="bad request",
        response=_Resp(),  # type: ignore[arg-type]
        body=None,
    )
    transport = FakeTransport(
        [{"label": "ok", "score": 1.0}],
        fail_times=1,
        fail_exc=exc,
    )
    client = ClaudeClient(
        settings=_settings(),
        transport=transport,
        cache=DiskCache(tmp_path),
        usage=LlmUsage(),
        sleep=lambda _t: None,
    )
    with pytest.raises(anthropic.APIStatusError):
        client.call_structured(
            model="claude-sonnet-5-5",
            prompt_version="test_v1",
            system="s",
            user_text="u",
            response_model=_TinyOut,
        )


def test_unavailable_without_key() -> None:
    client = ClaudeClient(
        settings=_settings(anthropic_api_key=None),
        transport=None,
    )
    assert not client.available
    client.warn_unavailable("test")
    assert client.warnings
