"""Load versioned prompt markdown files from ``engine/prompts/``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

PROMPT_LEGEND = "legend_v1"
PROMPT_ADJUDICATE = "adjudicate_v1"
PROMPT_BASELINE = "baseline_v1"


@lru_cache(maxsize=16)
def load_prompt(version: str) -> str:
    """Return prompt body for ``{version}.md`` (e.g. ``legend_v1``)."""
    path = PROMPTS_DIR / f"{version}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Missing prompt file: {path}")
    return path.read_text(encoding="utf-8")


def taxonomy_block() -> str:
    """Allowed category/subtype list for injection into user messages."""
    from takeoff_engine.models import SUBTYPES

    lines = ["Allowed category.subtype values:"]
    for cat, subs in SUBTYPES.items():
        for sub in subs:
            lines.append(f"- {cat}.{sub}")
    lines.append("- not_a_component  (adjudication only)")
    return "\n".join(lines)
