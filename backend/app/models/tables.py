"""ORM tables matching SPEC section 9.

Entity rows (rooms, detections, …) hang off analysis_runs so re-analysis can
create a new run without mutating prior corrections or results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid4())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sheets: Mapped[list[Sheet]] = relationship(back_populates="document")


class Sheet(Base):
    __tablename__ = "sheets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    sheet_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    page_width: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    page_height: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    viewport: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    legend_bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    scale_pt_per_ft: Mapped[float] = mapped_column(Float, nullable=False, default=18.0)
    current_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", use_alter=True, name="fk_sheets_current_run"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="sheets")
    runs: Mapped[list[AnalysisRun]] = relationship(
        back_populates="sheet",
        foreign_keys="AnalysisRun.sheet_id",
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sheet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sheets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Denormalized for idempotency: (file_hash, page_index, pipeline_version)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_versions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    timings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    llm_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    warnings: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sheet: Mapped[Sheet] = relationship(
        back_populates="runs",
        foreign_keys=[sheet_id],
    )
    rooms: Mapped[list[RoomRow]] = relationship(back_populates="run", cascade="all, delete-orphan")
    legend_entries: Mapped[list[LegendEntryRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    detections: Mapped[list[DetectionRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    wire_runs: Mapped[list[WireRunRow]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    boxes: Mapped[list[BoxRow]] = relationship(back_populates="run", cascade="all, delete-orphan")


class RoomRow(Base):
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sheet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    polygon: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    label_point: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")

    run: Mapped[AnalysisRun] = relationship(back_populates="rooms")


class LegendEntryRow(Base):
    __tablename__ = "legend_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    codes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subtype: Mapped[str | None] = mapped_column(String(64), nullable=True)
    combined: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    symbol_bbox: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    interpreted_by: Mapped[str] = mapped_column(String(16), nullable=False, default="rules")

    run: Mapped[AnalysisRun] = relationship(back_populates="legend_entries")


class DetectionRow(Base):
    __tablename__ = "detections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sheet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    subtype: Mapped[str] = mapped_column(String(64), nullable=False)
    codes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    mount_height_in: Mapped[float | None] = mapped_column(Float, nullable=True)
    center: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    bbox: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rotation_deg: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    room_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    room_source: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    run: Mapped[AnalysisRun] = relationship(back_populates="detections")


class WireRunRow(Base):
    __tablename__ = "wire_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sheet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    points: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    from_detection_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_detection_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cable_type: Mapped[str] = mapped_column(String(32), nullable=False)
    plan_length_ft: Mapped[float] = mapped_column(Float, nullable=False)
    vertical_allowance_ft: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_length_ft: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="user")

    run: Mapped[AnalysisRun] = relationship(back_populates="wire_runs")


class BoxRow(Base):
    __tablename__ = "boxes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sheet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    center: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    bbox: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    gangs: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    detection_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    cover: Mapped[str] = mapped_column(String(32), nullable=False, default="plate")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="user")

    run: Mapped[AnalysisRun] = relationship(back_populates="boxes")


class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sheet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity: Mapped[str] = mapped_column(String(32), nullable=False)  # detection|wire_run|box
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # create|update|delete
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
