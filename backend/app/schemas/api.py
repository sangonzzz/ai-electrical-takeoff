"""FastAPI request/response models layered on engine contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from takeoff_engine.models import (
    BBox,
    Bom,
    Box,
    Category,
    Detection,
    Evidence,
    LegendEntry,
    Point,
    Room,
    Sheet,
    Takeoff,
    WireRun,
)


class SheetJobInfo(BaseModel):
    sheet_id: str
    page_index: int
    job_id: str


class DocumentUploadResponse(BaseModel):
    document_id: str
    sheets: list[SheetJobInfo]


class JobStatusResponse(BaseModel):
    job_id: str
    sheet_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    progress: float = 0.0
    error: str | None = None
    pipeline_version: str | None = None
    human_reviewed: bool = False
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ReviewCompleteResponse(BaseModel):
    sheet_id: str
    job_id: str
    human_reviewed: bool = True


class DocumentSheetSummary(BaseModel):
    """Per-sheet row on GET /api/documents/{id} — includes job fields for polling."""

    sheet_id: str
    page_index: int
    sheet_number: str | None = None
    title: str | None = None
    current_run_id: str | None = None
    job_id: str | None = None
    status: Literal["queued", "running", "succeeded", "failed"] | None = None
    error: str | None = None


class DocumentDetailResponse(BaseModel):
    id: str
    filename: str
    file_hash: str
    page_count: int
    created_at: datetime
    sheets: list[DocumentSheetSummary]


class SheetDetailResponse(BaseModel):
    sheet: Sheet
    job: JobStatusResponse | None = None
    legend: list[LegendEntry] = []
    rooms: list[Room] = []
    detections: list[Detection] = []
    wire_runs: list[WireRun] = []
    boxes: list[Box] = []
    takeoff: Takeoff | None = None
    warnings: list[str] = []


class DetectionCreate(BaseModel):
    category: Category
    subtype: str
    codes: list[str] = []
    mount_height_in: float | None = None
    center: Point
    bbox: BBox | None = None
    rotation_deg: Literal[0, 90, 180, 270] = 0
    room_id: str | None = None
    room_source: Literal["auto", "manual"] = "auto"
    confidence: float = Field(default=1.0, ge=0, le=1)
    needs_review: bool = False
    evidence: Evidence = Field(default_factory=Evidence)


class DetectionPatch(BaseModel):
    category: Category | None = None
    subtype: str | None = None
    codes: list[str] | None = None
    mount_height_in: float | None = None
    center: Point | None = None
    bbox: BBox | None = None
    rotation_deg: Literal[0, 90, 180, 270] | None = None
    room_id: str | None = None
    room_source: Literal["auto", "manual"] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    needs_review: bool | None = None
    evidence: Evidence | None = None


class DetectionMutationResponse(BaseModel):
    detection: Detection
    takeoff: Takeoff


class WireRunCreate(BaseModel):
    points: list[Point]
    from_detection_id: str | None = None
    to_detection_id: str | None = None
    cable_type: Literal["nm_14_2", "nm_14_3"]
    plan_length_ft: float
    vertical_allowance_ft: float = 0.0
    total_length_ft: float | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)


class WireRunPatch(BaseModel):
    points: list[Point] | None = None
    from_detection_id: str | None = None
    to_detection_id: str | None = None
    cable_type: Literal["nm_14_2", "nm_14_3"] | None = None
    plan_length_ft: float | None = None
    vertical_allowance_ft: float | None = None
    total_length_ft: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class BoxCreate(BaseModel):
    center: Point
    bbox: BBox | None = None
    kind: Literal["device", "fan_rated", "ceiling_round", "none"]
    gangs: int = 1
    detection_ids: list[str] = []
    cover: Literal["plate", "weatherproof_cover", "none"] = "plate"


class BoxPatch(BaseModel):
    center: Point | None = None
    bbox: BBox | None = None
    kind: Literal["device", "fan_rated", "ceiling_round", "none"] | None = None
    gangs: int | None = None
    detection_ids: list[str] | None = None
    cover: Literal["plate", "weatherproof_cover", "none"] | None = None


class EntityMutationResponse(BaseModel):
    """Generic mutation response that always returns recomputed takeoff/bom context."""

    takeoff: Takeoff
    bom: Bom | None = None
    detection: Detection | None = None
    wire_run: WireRun | None = None
    box: Box | None = None


class CorrectionOut(BaseModel):
    id: str
    sheet_id: str
    analysis_run_id: str
    entity: str
    entity_id: str
    action: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    created_at: datetime


class ReanalyzeResponse(BaseModel):
    sheet_id: str
    job_id: str
    status: str
