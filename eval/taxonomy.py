"""Shared taxonomy helpers for eval (mirrors SPEC section 2 / models.SUBTYPES)."""

from __future__ import annotations

from takeoff_engine.models import SUBTYPES

# Reviewers weigh fans and lights most; reports call these out explicitly.
HIGHLIGHT_CATEGORIES: frozenset[str] = frozenset({"ceiling_fan", "light"})


def all_subtype_keys() -> list[str]:
    """Return every ``category.subtype`` key in taxonomy order."""
    return [f"{cat}.{sub}" for cat, subs in SUBTYPES.items() for sub in subs]


def type_key(category: str, subtype: str) -> str:
    """Build the count / match key ``category.subtype``."""
    return f"{category}.{subtype}"


def category_of(type_key_str: str) -> str:
    """Extract category from a ``category.subtype`` key."""
    return type_key_str.split(".", 1)[0]
