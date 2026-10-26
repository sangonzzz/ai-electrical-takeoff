"""Stable LLM content ids (cache across uuid4 remints)."""

from __future__ import annotations

from takeoff_engine.llm.ids import stable_candidate_id, stable_legend_id


def test_stable_legend_id_deterministic() -> None:
    a = stable_legend_id("SWITCH", ["D"], (1.0, 2.0, 3.0, 4.0))
    b = stable_legend_id("SWITCH", ["D"], (1.0, 2.0, 3.0, 4.0))
    c = stable_legend_id("SWITCH", ["D"], (1.01, 2.0, 3.0, 4.0))
    assert a == b
    assert a != c
    assert a.startswith("L")


def test_stable_candidate_id_deterministic() -> None:
    a = stable_candidate_id(0, (10.0, 20.0, 30.0, 40.0))
    b = stable_candidate_id(0, (10.0, 20.0, 30.0, 40.0))
    c = stable_candidate_id(1, (10.0, 20.0, 30.0, 40.0))
    assert a == b
    assert a != c
