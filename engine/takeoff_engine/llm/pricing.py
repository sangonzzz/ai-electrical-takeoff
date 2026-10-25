"""USD cost estimates from Anthropic list prices (per million tokens).

Used only for LlmUsage.cost_usd reporting — not billing. Update when env
model IDs change. Source: platform.claude.com pricing (2026-10).
"""

from __future__ import annotations

# (input_usd_per_mtok, output_usd_per_mtok)
_PRICES: dict[str, tuple[float, float]] = {
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-opus-5-5": (4.0, 20.0),
    # Fallbacks for older env values during transition
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

_DEFAULT = (3.0, 15.0)  # conservative unknown-model estimate


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return estimated USD for one call."""
    key = model.strip().lower()
    rates = _PRICES.get(key)
    if rates is None:
        for name, price in _PRICES.items():
            if name in key:
                rates = price
                break
    if rates is None:
        rates = _DEFAULT
    inp, out = rates
    return (input_tokens / 1_000_000.0) * inp + (output_tokens / 1_000_000.0) * out
