"""Enum validation for LLM response schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from takeoff_engine.llm.schemas import (
    AdjudicationItem,
    LegendEntryInterpretation,
)


def test_legend_rejects_bad_subtype() -> None:
    with pytest.raises(ValidationError):
        LegendEntryInterpretation(
            entry_id="x",
            category="switch",
            subtype="not_a_real_subtype",
            reason="bad",
        )


def test_legend_allows_nulls() -> None:
    item = LegendEntryInterpretation(
        entry_id="x",
        category=None,
        subtype=None,
        reason="plumbing",
    )
    assert item.category is None


def test_adjudication_rejects_coords_shaped_labels() -> None:
    with pytest.raises(ValidationError):
        AdjudicationItem(
            candidate_id="c1",
            label="somewhere_at_100_200",
            confidence=0.5,
            reason="nope",
        )


def test_adjudication_allows_not_a_component() -> None:
    item = AdjudicationItem(
        candidate_id="c1",
        label="not_a_component",
        confidence=0.9,
        reason="wiring",
    )
    assert item.label == "not_a_component"
