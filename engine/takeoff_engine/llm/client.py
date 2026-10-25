"""Anthropic Claude wrapper: tool-use structured output, retries, usage, cache.

Principle: Claude answers WHAT, never WHERE. Every response is validated with
Pydantic. Without an API key the engine still runs (rules only) with a warning.
"""

from __future__ import annotations

import base64
import json
import logging
import random
import time
from pathlib import Path
from typing import Any, Callable, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from takeoff_engine.config import Settings, get_settings
from takeoff_engine.llm.cache import DiskCache, cache_key
from takeoff_engine.llm.pricing import estimate_cost_usd
from takeoff_engine.models import LlmUsage

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

TOOL_NAME = "submit_result"
MAX_TRANSPORT_ATTEMPTS = 3
VALIDATION_RETRIES = 1  # one extra attempt after a validation error


class Transport(Protocol):
    """Minimal surface so tests inject a fake without the network."""

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: dict[str, Any],
    ) -> Any: ...


class AnthropicTransport:
    """Real Anthropic Messages API transport."""

    def __init__(self, api_key: str) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: dict[str, Any],
    ) -> Any:
        return self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )


def _is_retryable(exc: BaseException) -> bool:
    import anthropic

    if isinstance(exc, (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError)):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        status = getattr(exc, "status_code", None)
        if status == 429 or (isinstance(status, int) and status >= 500):
            return True
    # Some SDK versions wrap overloaded / service unavailable
    if isinstance(exc, (anthropic.OverloadedError, anthropic.ServiceUnavailableError)):
        return True
    return False


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff with full jitter. attempt is 0-based."""
    base = 0.5 * (2**attempt)
    return random.uniform(0.0, base)


def _image_block(png_bytes: bytes, media_type: str = "image/png") -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.standard_b64encode(png_bytes).decode("ascii"),
        },
    }


def _strictify_schema(node: Any) -> None:
    """In-place: additionalProperties=false + required=all props (Sonnet 5.5 strict)."""
    if not isinstance(node, dict):
        return
    if "properties" in node and isinstance(node["properties"], dict):
        node["type"] = "object"
        node["additionalProperties"] = False
        node["required"] = list(node["properties"].keys())
        for child in node["properties"].values():
            _strictify_schema(child)
    if "$defs" in node and isinstance(node["$defs"], dict):
        for child in node["$defs"].values():
            _strictify_schema(child)
    if "definitions" in node and isinstance(node["definitions"], dict):
        for child in node["definitions"].values():
            _strictify_schema(child)
    if "items" in node:
        _strictify_schema(node["items"])
    for key in ("anyOf", "oneOf", "allOf"):
        if key in node and isinstance(node[key], list):
            for child in node[key]:
                _strictify_schema(child)


def _tool_schema(response_model: type[BaseModel]) -> dict[str, Any]:
    """JSON Schema for Anthropic strict tool input."""
    schema = response_model.model_json_schema()
    schema.pop("title", None)
    _strictify_schema(schema)
    return schema


def _ensure_repo_dotenv() -> None:
    """Load repo ``.env`` into os.environ if ANTHROPIC_API_KEY is unset."""
    import os

    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    root = Path(__file__).resolve().parents[3]
    env_path = root / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _extract_tool_input(message: Any) -> dict[str, Any]:
    content = getattr(message, "content", None) or []
    for block in content:
        btype = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
        if btype != "tool_use":
            continue
        name = block.get("name") if isinstance(block, dict) else getattr(block, "name", None)
        if name != TOOL_NAME:
            continue
        raw = block.get("input") if isinstance(block, dict) else getattr(block, "input", None)
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            return json.loads(raw)
    raise ValueError(f"No tool_use block named {TOOL_NAME!r} in model response")


def _usage_from_message(message: Any) -> tuple[int, int]:
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0, 0
    if isinstance(usage, dict):
        return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
    return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)


class ClaudeClient:
    """Structured Claude calls with cache, retries, and LlmUsage accounting."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        transport: Transport | None = None,
        cache: DiskCache | None = None,
        usage: LlmUsage | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if settings is None:
            _ensure_repo_dotenv()
        self.settings = settings or get_settings()
        self.usage = usage if usage is not None else LlmUsage()
        self.cache = cache if cache is not None else DiskCache()
        self._sleep = sleep
        self.warnings: list[str] = []

        self._transport: Transport | None = transport
        if self._transport is None and self.settings.anthropic_api_key:
            self._transport = AnthropicTransport(self.settings.anthropic_api_key)

    @property
    def available(self) -> bool:
        return self._transport is not None

    def warn_unavailable(self, task: str) -> None:
        msg = (
            f"LLM unavailable for {task}: no ANTHROPIC_API_KEY (or ENABLE_LLM off). "
            "Continuing with rules only."
        )
        logger.warning(msg)
        self.warnings.append(msg)

    def call_structured(
        self,
        *,
        model: str,
        prompt_version: str,
        system: str,
        user_text: str,
        response_model: type[T],
        images: list[bytes] | None = None,
        max_tokens: int = 4096,
        use_cache: bool = True,
        cache_extra: dict[str, Any] | None = None,
    ) -> T:
        """Call Claude with structured tool use; validate; cache the parsed JSON.

        Claude Sonnet 5.5 rejects forced ``tool_choice`` (``tool`` / ``any``).
        We use ``auto`` + ``strict: true`` and instruct the model to call the tool.
        """
        if not self.available:
            raise RuntimeError("ClaudeClient has no transport (missing API key)")

        images = images or []
        key = cache_key(
            model,
            prompt_version,
            text_parts=[system, user_text],
            image_parts=images,
            extra=cache_extra,
        )

        if use_cache:
            cached = self.cache.get(key)
            if cached is not None:
                self.usage.cache_hits += 1
                logger.info(
                    "LLM cache hit model=%s prompt=%s key=%s",
                    model,
                    prompt_version,
                    key[:12],
                )
                return response_model.model_validate(cached)

        tools = [
            {
                "name": TOOL_NAME,
                "description": "Submit the structured result. Never include coordinates.",
                "input_schema": _tool_schema(response_model),
                "strict": True,
            }
        ]
        # Sonnet 5.5: only auto/none — never type "tool" or "any"
        tool_choice = {"type": "auto"}

        must_tool = (
            f"You MUST call the {TOOL_NAME} tool exactly once with your full answer. "
            "Do not reply with plain text only. Never include coordinates."
        )
        system_full = f"{system.rstrip()}\n\n{must_tool}"
        user_full = f"{user_text.rstrip()}\n\n{must_tool}"

        user_content: list[dict[str, Any]] = []
        for img in images:
            user_content.append(_image_block(img))
        user_content.append({"type": "text", "text": user_full})

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]

        last_validation_error: str | None = None
        parsed: T | None = None

        for validation_round in range(VALIDATION_RETRIES + 1):
            if last_validation_error is not None:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous tool input failed validation. Fix it and "
                            f"call {TOOL_NAME} again.\n\nError:\n{last_validation_error}"
                        ),
                    }
                )

            message = self._create_with_retries(
                model=model,
                max_tokens=max_tokens,
                system=system_full,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
            )
            inp_tok, out_tok = _usage_from_message(message)
            self._record_usage(model, inp_tok, out_tok)

            # Keep assistant turn for a possible validation retry
            messages.append({"role": "assistant", "content": _serialize_content(message)})

            try:
                raw = _extract_tool_input(message)
                parsed = response_model.model_validate(raw)
                break
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                last_validation_error = str(exc)
                logger.warning(
                    "LLM validation failed (round %s): %s",
                    validation_round,
                    last_validation_error[:300],
                )
                if validation_round >= VALIDATION_RETRIES:
                    raise

        assert parsed is not None
        if use_cache:
            self.cache.set(key, parsed.model_dump(mode="json"))
        return parsed

    def _create_with_retries(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_choice: dict[str, Any],
    ) -> Any:
        assert self._transport is not None
        last_exc: BaseException | None = None
        for attempt in range(MAX_TRANSPORT_ATTEMPTS):
            try:
                return self._transport.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                )
            except Exception as exc:  # noqa: BLE001 — filter via _is_retryable
                last_exc = exc
                if not _is_retryable(exc) or attempt >= MAX_TRANSPORT_ATTEMPTS - 1:
                    raise
                delay = _backoff_seconds(attempt)
                logger.warning(
                    "LLM transport retry %s/%s after %s; sleep %.2fs",
                    attempt + 1,
                    MAX_TRANSPORT_ATTEMPTS,
                    type(exc).__name__,
                    delay,
                )
                self._sleep(delay)
        assert last_exc is not None
        raise last_exc

    def _record_usage(self, model: str, input_tokens: int, output_tokens: int) -> None:
        cost = estimate_cost_usd(model, input_tokens, output_tokens)
        self.usage.calls += 1
        self.usage.input_tokens += input_tokens
        self.usage.output_tokens += output_tokens
        self.usage.cost_usd += cost
        logger.info(
            "LLM call model=%s in=%s out=%s cost_usd=%.6f totals calls=%s cost=%.6f",
            model,
            input_tokens,
            output_tokens,
            cost,
            self.usage.calls,
            self.usage.cost_usd,
        )


def _serialize_content(message: Any) -> list[dict[str, Any]]:
    """Turn SDK content blocks into JSON-serializable message content."""
    out: list[dict[str, Any]] = []
    content = getattr(message, "content", None) or []
    for block in content:
        if isinstance(block, dict):
            out.append(block)
            continue
        btype = getattr(block, "type", None)
        if btype == "tool_use":
            out.append(
                {
                    "type": "tool_use",
                    "id": getattr(block, "id", "tool_0"),
                    "name": getattr(block, "name", TOOL_NAME),
                    "input": getattr(block, "input", {}),
                }
            )
        elif btype == "text":
            out.append({"type": "text", "text": getattr(block, "text", "")})
        else:
            # Best-effort dump
            if hasattr(block, "model_dump"):
                out.append(block.model_dump())
    return out


def make_client(
    *,
    usage: LlmUsage | None = None,
    transport: Transport | None = None,
    cache: DiskCache | None = None,
    settings: Settings | None = None,
) -> ClaudeClient:
    """Factory that respects ENABLE_LLM and missing keys."""
    _ensure_repo_dotenv()
    cfg = settings or get_settings()
    if not cfg.enable_llm:
        # Force unavailable even if a key is present
        return ClaudeClient(settings=cfg, transport=None, cache=cache, usage=usage)
    return ClaudeClient(settings=cfg, transport=transport, cache=cache, usage=usage)
