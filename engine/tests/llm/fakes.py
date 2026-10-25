"""Fake Anthropic transport for offline tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class FakeToolUse:
    type: str = "tool_use"
    id: str = "toolu_test"
    name: str = "submit_result"
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeMessage:
    content: list[Any]
    usage: FakeUsage = field(default_factory=FakeUsage)


class FakeTransport:
    """Returns canned tool_use payloads; records call kwargs."""

    def __init__(
        self,
        payloads: list[dict[str, Any]] | Callable[[dict[str, Any]], dict[str, Any]],
        *,
        fail_times: int = 0,
        fail_exc: BaseException | None = None,
    ) -> None:
        self._payloads = payloads
        self._index = 0
        self.calls: list[dict[str, Any]] = []
        self._fail_times = fail_times
        self._fail_exc = fail_exc
        self._failures_done = 0

    def create(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(kwargs)
        if self._failures_done < self._fail_times:
            self._failures_done += 1
            assert self._fail_exc is not None
            raise self._fail_exc

        if callable(self._payloads):
            payload = self._payloads(kwargs)
        else:
            if self._index >= len(self._payloads):
                payload = self._payloads[-1]
            else:
                payload = self._payloads[self._index]
                self._index += 1
        return FakeMessage(content=[FakeToolUse(input=payload)])


def tiny_png() -> bytes:
    """1x1 PNG (valid image bytes for cache keying / message building)."""
    # Minimal PNG from PIL would need import; hardcode a known 1x1 red PNG
    import base64

    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
