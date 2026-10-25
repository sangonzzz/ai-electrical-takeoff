"""Initial schema: documents, sheets, runs, entities, corrections.

Revision ID: 001
Revises:
Create Date: 2026-10-25

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"])

    op.create_table(
        "sheets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("sheet_number", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("page_width", sa.Float(), nullable=False),
        sa.Column("page_height", sa.Float(), nullable=False),
        sa.Column("viewport", postgresql.JSONB(), nullable=False),
        sa.Column("legend_bbox", postgresql.JSONB(), nullable=True),
        sa.Column("scale_pt_per_ft", sa.Float(), nullable=False),
        sa.Column("current_run_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sheets_document_id", "sheets", ["document_id"])

    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sheet_id", sa.String(length=36), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_versions", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("timings", postgresql.JSONB(), nullable=False),
        sa.Column("llm_usage", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sheet_id"], ["sheets.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analysis_runs_sheet_id", "analysis_runs", ["sheet_id"])
    op.create_index("ix_analysis_runs_file_hash", "analysis_runs", ["file_hash"])
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"])

    op.create_foreign_key(
        "fk_sheets_current_run",
        "sheets",
        "analysis_runs",
        ["current_run_id"],
        ["id"],
    )

    op.create_table(
        "rooms",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("sheet_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("polygon", postgresql.JSONB(), nullable=False),
        sa.Column("label_point", postgresql.JSONB(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_rooms_analysis_run_id", "rooms", ["analysis_run_id"])
    op.create_index("ix_rooms_sheet_id", "rooms", ["sheet_id"])

    op.create_table(
        "legend_entries",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("codes", postgresql.JSONB(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("subtype", sa.String(length=64), nullable=True),
        sa.Column("combined", sa.Boolean(), nullable=False),
        sa.Column("symbol_bbox", postgresql.JSONB(), nullable=False),
        sa.Column("interpreted_by", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_legend_entries_analysis_run_id", "legend_entries", ["analysis_run_id"])

    op.create_table(
        "detections",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("sheet_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("subtype", sa.String(length=64), nullable=False),
        sa.Column("codes", postgresql.JSONB(), nullable=False),
        sa.Column("mount_height_in", sa.Float(), nullable=True),
        sa.Column("center", postgresql.JSONB(), nullable=False),
        sa.Column("bbox", postgresql.JSONB(), nullable=False),
        sa.Column("rotation_deg", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.String(length=64), nullable=True),
        sa.Column("room_source", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_detections_analysis_run_id", "detections", ["analysis_run_id"])
    op.create_index("ix_detections_sheet_id", "detections", ["sheet_id"])

    op.create_table(
        "wire_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("sheet_id", sa.String(length=36), nullable=False),
        sa.Column("points", postgresql.JSONB(), nullable=False),
        sa.Column("from_detection_id", sa.String(length=64), nullable=True),
        sa.Column("to_detection_id", sa.String(length=64), nullable=True),
        sa.Column("cable_type", sa.String(length=32), nullable=False),
        sa.Column("plan_length_ft", sa.Float(), nullable=False),
        sa.Column("vertical_allowance_ft", sa.Float(), nullable=False),
        sa.Column("total_length_ft", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_wire_runs_analysis_run_id", "wire_runs", ["analysis_run_id"])
    op.create_index("ix_wire_runs_sheet_id", "wire_runs", ["sheet_id"])

    op.create_table(
        "boxes",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("sheet_id", sa.String(length=36), nullable=False),
        sa.Column("center", postgresql.JSONB(), nullable=False),
        sa.Column("bbox", postgresql.JSONB(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("gangs", sa.Integer(), nullable=False),
        sa.Column("detection_ids", postgresql.JSONB(), nullable=False),
        sa.Column("cover", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_boxes_analysis_run_id", "boxes", ["analysis_run_id"])
    op.create_index("ix_boxes_sheet_id", "boxes", ["sheet_id"])

    op.create_table(
        "corrections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sheet_id", sa.String(length=36), nullable=False),
        sa.Column("analysis_run_id", sa.String(length=36), nullable=False),
        sa.Column("entity", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_corrections_sheet_id", "corrections", ["sheet_id"])
    op.create_index("ix_corrections_analysis_run_id", "corrections", ["analysis_run_id"])


def downgrade() -> None:
    op.drop_table("corrections")
    op.drop_table("boxes")
    op.drop_table("wire_runs")
    op.drop_table("detections")
    op.drop_table("legend_entries")
    op.drop_table("rooms")
    op.drop_constraint("fk_sheets_current_run", "sheets", type_="foreignkey")
    op.drop_table("analysis_runs")
    op.drop_table("sheets")
    op.drop_table("documents")
