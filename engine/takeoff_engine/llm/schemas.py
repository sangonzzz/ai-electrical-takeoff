"""Pydantic response schemas for Claude tool-use structured output.

These are internal to the LLM layer — not part of the frozen SheetResult
contract. Labels must still validate against SPEC section 2 enums.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from takeoff_engine.models import SUBTYPES, Category

# All "category.subtype" labels plus the reject label. Claude never returns coords.
ALLOWED_ADJUDICATION_LABELS: frozenset[str] = frozenset(
    {f"{cat}.{sub}" for cat, subs in SUBTYPES.items() for sub in subs}
    | {"not_a_component"}
)

ALLOWED_CATEGORIES: frozenset[str] = frozenset(c.value for c in Category)


def _subtype_ok(category: str | None, subtype: str | None) -> bool:
    if category is None and subtype is None:
        return True
    if category is None or subtype is None:
        # subtype without category (or vice versa) is invalid for our merge
        return category is not None and subtype is None
    allowed = SUBTYPES.get(category, [])
    return subtype in allowed


class LegendEntryInterpretation(BaseModel):
    """One legend row after Claude reads the symbol + description."""

    entry_id: str
    category: str | None = None
    subtype: str | None = None
    code_meanings: dict[str, str] = Field(default_factory=dict)
    combined: bool = False
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("category")
    @classmethod
    def _category_enum(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"category {v!r} not in allowed set {sorted(ALLOWED_CATEGORIES)}"
            )
        return v

    @model_validator(mode="after")
    def _subtype_matches_category(self) -> LegendEntryInterpretation:
        if not _subtype_ok(self.category, self.subtype):
            allowed = SUBTYPES.get(self.category or "", [])
            raise ValueError(
                f"subtype {self.subtype!r} invalid for category {self.category!r}; "
                f"allowed: {allowed}"
            )
        return self


class LegendInterpretResponse(BaseModel):
    """Tool payload for interpret_legend."""

    entries: list[LegendEntryInterpretation]


class AdjudicationItem(BaseModel):
    """One candidate label — WHAT only, never WHERE."""

    candidate_id: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("label")
    @classmethod
    def _label_allowed(cls, v: str) -> str:
        if v not in ALLOWED_ADJUDICATION_LABELS:
            raise ValueError(
                f"label {v!r} not allowed; must be category.subtype or "
                f"'not_a_component'"
            )
        return v


class AdjudicateResponse(BaseModel):
    """Tool payload for adjudicate (batched crops)."""

    items: list[AdjudicationItem]


class RoomCounts(BaseModel):
    """Counts for one room in the LLM-only baseline (no geometry)."""

    room_name: str
    counts: dict[str, int] = Field(default_factory=dict)

    @field_validator("counts")
    @classmethod
    def _non_negative(cls, v: dict[str, int]) -> dict[str, int]:
        for k, n in v.items():
            if n < 0:
                raise ValueError(f"count for {k!r} must be >= 0, got {n}")
        return v


class BaselineVisionResponse(BaseModel):
    """LLM-only takeoff baseline: room_name -> count keys."""

    rooms: list[RoomCounts]
    notes: str = ""


# Literal helper for prompts / docs
LabelLiteral = Literal[
    "ceiling_fan.ceiling_fan",
    "ceiling_fan.fan_light",
    "light.recessed",
    "light.recessed_vapor_proof",
    "light.pendant",
    "light.wall",
    "light.exterior_wall",
    "switch.single_pole",
    "switch.three_way",
    "switch.three_way_dimmer",
    "switch.dimmer",
    "switch.fan",
    "switch.vacancy_sensor",
    "switch.astronomical_timer",
    "receptacle.duplex",
    "receptacle.afci",
    "receptacle.afci_half_hot",
    "receptacle.gfci",
    "receptacle.gfci_weatherproof",
    "receptacle.gfci_240v",
    "receptacle.gfci_microwave",
    "receptacle.gfci_dishwasher",
    "receptacle.range_hood",
    "receptacle.fan_coil_dedicated",
    "receptacle.240v",
    "exhaust_fan.bath_exhaust",
    "exhaust_fan.indoor_air_quality",
    "detector.smoke",
    "detector.smoke_co",
    "junction_box.junction_box",
    "not_a_component",
]
