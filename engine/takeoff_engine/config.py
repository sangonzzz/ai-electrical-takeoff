"""Thresholds and environment settings for the takeoff engine.

Named constants document *why* a number exists so agents do not silently retune
them. Env settings gate LLM and BOM without changing code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Max gap (pt) between primitive bboxes when clustering a symbol. "$" is an S
# crossing a bar that may not share endpoints, so proximity matters more than
# shared vertices.
SYMBOL_CLUSTER_GAP_PT = 1.0

# Search radius (pt) around a cluster for device code text (D, GFI, WP, ...).
CODE_TEXT_RADIUS_PT = 14.0

# Max distance (pt) along a wall between switches that share one multi-gang box.
GANG_GROUP_DIST_PT = 10.0

# Max snap distance (pt) from a dashed wire endpoint to a device center.
WIRE_SNAP_PT = 10.0

# Fallback scale when SCALE: text cannot be parsed. 1/4" = 1'-0" => 18 pt = 1 ft.
DEFAULT_PT_PER_FT = 18.0

# Approximate electrical viewports for local development only. Production code
# must discover the viewport dynamically (Agente 2). Page 2 is unknown until
# measured — derive it from title/frame geometry.
APPROX_VIEWPORTS: dict[int, tuple[float, float, float, float]] = {
    0: (860.0, 40.0, 1440.0, 840.0),  # Plan 1
    1: (180.0, 90.0, 1300.0, 520.0),  # Plan 2
    # 2: unknown — derive later from electrical title cell
    3: (1040.0, 40.0, 1880.0, 700.0),  # Plan 4
}


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    anthropic_api_key: str | None
    anthropic_model: str
    anthropic_model_cheap: str
    enable_llm: bool
    enable_bom: bool


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    """Load settings from the process environment."""
    return Settings(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        anthropic_model_cheap=os.environ.get("ANTHROPIC_MODEL_CHEAP", "claude-haiku-5-5"),
        enable_llm=_env_bool("ENABLE_LLM", default=True),
        enable_bom=_env_bool("ENABLE_BOM", default=True),
    )
