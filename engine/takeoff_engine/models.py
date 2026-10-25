"""Shared Pydantic contracts for the takeoff engine and backend.

Coordinates are PDF points in page space, origin top-left (PyMuPDF convention).
One sheet = one page. Contract changes go through Agente 1 only.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "1.0.0"


class Category(StrEnum):
    CEILING_FAN = "ceiling_fan"
    LIGHT = "light"
    SWITCH = "switch"
    RECEPTACLE = "receptacle"
    EXHAUST_FAN = "exhaust_fan"
    DETECTOR = "detector"
    JUNCTION_BOX = "junction_box"


# Taxonomy from SPEC section 2. Count keys are "category" and "category.subtype".
SUBTYPES: dict[str, list[str]] = {
    "ceiling_fan": ["ceiling_fan", "fan_light"],
    "light": ["recessed", "recessed_vapor_proof", "pendant", "wall", "exterior_wall"],
    "switch": [
        "single_pole",
        "three_way",
        "three_way_dimmer",
        "dimmer",
        "fan",
        "vacancy_sensor",
        "astronomical_timer",
    ],
    "receptacle": [
        "duplex",
        "afci",
        "afci_half_hot",
        "gfci",
        "gfci_weatherproof",
        "gfci_240v",
        "gfci_microwave",
        "gfci_dishwasher",
        "range_hood",
        "fan_coil_dedicated",
        "240v",
    ],
    "exhaust_fan": ["bath_exhaust", "indoor_air_quality"],
    "detector": ["smoke", "smoke_co"],
    "junction_box": ["junction_box"],
}


class Point(BaseModel):
    x: float
    y: float


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class Evidence(BaseModel):
    legend_entry_id: str | None = None
    match_score: float | None = None  # 0..1 similarity to the legend symbol
    text_tokens: list[str] = []  # tokens found near the symbol
    llm_label: str | None = None
    llm_reason: str | None = None
    notes: list[str] = []


class Detection(BaseModel):
    id: str  # uuid4
    sheet_id: str
    category: Category
    subtype: str
    codes: list[str] = []
    mount_height_in: float | None = None
    center: Point
    bbox: BBox
    rotation_deg: Literal[0, 90, 180, 270] = 0
    room_id: str | None = None
    room_source: Literal["auto", "manual"] = "auto"
    confidence: float = Field(ge=0, le=1)
    source: Literal["geometry", "llm", "user"]
    status: Literal["active", "deleted"] = "active"
    needs_review: bool = False
    evidence: Evidence = Field(default_factory=Evidence)

    @model_validator(mode="after")
    def _subtype_belongs_to_category(self) -> Detection:
        allowed = SUBTYPES.get(self.category.value, [])
        if self.subtype not in allowed:
            raise ValueError(
                f"subtype {self.subtype!r} is not valid for category {self.category.value!r}; "
                f"allowed: {allowed}"
            )
        return self


class Room(BaseModel):
    id: str
    sheet_id: str
    name: str  # raw label text, e.g. "KITCHEN / DINING"
    display_name: str  # e.g. "Kitchen / Dining", "CL 2", "Exterior", "Attic"
    kind: Literal["interior", "exterior", "attic"]
    polygon: list[Point]  # exterior ring; empty for "Exterior" (outside footprint)
    label_point: Point | None = None
    source: Literal["auto", "manual"] = "auto"


class LegendEntry(BaseModel):
    id: str
    description: str  # text from the legend row
    codes: list[str] = []  # code tokens printed with the legend symbol
    category: Category | None = None
    subtype: str | None = None
    combined: bool = False
    symbol_bbox: BBox
    interpreted_by: Literal["rules", "llm"] = "rules"


class WireRun(BaseModel):
    id: str
    sheet_id: str
    points: list[Point]  # polyline following the dashed line
    from_detection_id: str | None
    to_detection_id: str | None
    cable_type: Literal["nm_14_2", "nm_14_3"]
    plan_length_ft: float
    vertical_allowance_ft: float
    total_length_ft: float
    confidence: float
    source: Literal["geometry", "user"]


class Box(BaseModel):
    id: str
    sheet_id: str
    center: Point
    bbox: BBox
    kind: Literal["device", "fan_rated", "ceiling_round", "none"]
    gangs: int  # 1, 2, 3...
    detection_ids: list[str]
    cover: Literal["plate", "weatherproof_cover", "none"]
    source: Literal["geometry", "user"]


class SheetImage(BaseModel):
    url: str | None = None  # filled by backend
    dpi: int
    origin: Point  # viewport top-left in PDF points
    width_px: int
    height_px: int


class Sheet(BaseModel):
    id: str
    document_id: str | None = None
    page_index: int  # 0-based
    sheet_number: str | None = None  # "A1-111"
    title: str | None = None  # "ELECTRICAL PLAN - PLAN 1"
    page_width: float
    page_height: float
    viewport: BBox
    legend_bbox: BBox | None = None
    scale_pt_per_ft: float
    image: SheetImage | None = None


class LlmUsage(BaseModel):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cache_hits: int = 0


class SheetResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    pipeline_version: str
    sheet: Sheet
    legend: list[LegendEntry]
    rooms: list[Room]
    detections: list[Detection]
    wire_runs: list[WireRun] = []
    boxes: list[Box] = []
    warnings: list[str] = []
    timings_ms: dict[str, float] = {}
    llm_usage: LlmUsage = Field(default_factory=LlmUsage)


class TakeoffRow(BaseModel):
    room_id: str
    room_name: str
    counts: dict[str, int]  # keys: "light" and "light.recessed", etc.


class Takeoff(BaseModel):
    sheet_id: str
    rows: list[TakeoffRow]
    totals: dict[str, int]
    unassigned: dict[str, int]


class BomLine(BaseModel):
    item_key: str
    description: str
    quantity: float
    unit: str
    unit_price: float | None
    extended_price: float | None
    price_source: str | None
    source_ids: list[str] = []  # detection / box / wire ids behind this line


class Bom(BaseModel):
    sheet_id: str
    lines: list[BomLine]
    total_usd: float
    assumptions: dict[str, float | str]
