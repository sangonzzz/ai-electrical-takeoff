"""Claude LLM tasks for legend interpretation and adjudication (owned by Agente 4).

Claude answers WHAT a symbol means, never WHERE it is. Structured tool-use
output is validated with Pydantic and cached under ``.cache/llm/``. Without an
API key the engine still runs (rules only) with a warning.

Optional kwargs ``usage`` / ``warnings`` / ``client`` let the pipeline collect
``LlmUsage`` and merge warnings into ``SheetResult`` without changing the
required call shape Agente 2 already stubs.
"""

from __future__ import annotations

from takeoff_engine.llm.adjudicate_task import adjudicate
from takeoff_engine.llm.baseline import baseline_vision_takeoff
from takeoff_engine.llm.client import ClaudeClient, make_client
from takeoff_engine.llm.legend import interpret_legend
from takeoff_engine.llm.prompts import PROMPT_ADJUDICATE, PROMPT_BASELINE, PROMPT_LEGEND

__all__ = [
    "ClaudeClient",
    "PROMPT_ADJUDICATE",
    "PROMPT_BASELINE",
    "PROMPT_LEGEND",
    "adjudicate",
    "baseline_vision_takeoff",
    "interpret_legend",
    "make_client",
]
