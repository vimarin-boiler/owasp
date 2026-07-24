"""Add scoring snapshots metadata and recommendation roadmap fields.

Revision ID: 0004_scoring_recommendations
Revises: 0003_assessment_workflow
Create Date: 2026-07-24
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_scoring_recommendations"
down_revision: Union[str, None] = "0003_assessment_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("assessment_score_snapshots", schema=None) as batch_op:
        batch_op.add_column(sa.Column("input_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("status_summary", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("calculation_metadata", sa.JSON(), nullable=True))
        batch_op.create_index(batch_op.f("ix_assessment_score_snapshots_input_hash"), ["input_hash"], unique=False)
        batch_op.create_index(batch_op.f("ix_assessment_score_snapshots_is_published_snapshot"), ["is_published_snapshot"], unique=False)
        batch_op.create_index(batch_op.f("ix_assessment_score_snapshots_scoring_source"), ["scoring_source"], unique=False)

    op.execute("UPDATE assessment_score_snapshots SET input_hash = '' WHERE input_hash IS NULL")
    op.execute("UPDATE assessment_score_snapshots SET status_summary = '{}' WHERE status_summary IS NULL")
    op.execute("UPDATE assessment_score_snapshots SET calculation_metadata = '{}' WHERE calculation_metadata IS NULL")
    with op.batch_alter_table("assessment_score_snapshots", schema=None) as batch_op:
        batch_op.alter_column("input_hash", existing_type=sa.String(length=64), nullable=False)
        batch_op.alter_column("status_summary", existing_type=sa.JSON(), nullable=False)
        batch_op.alter_column("calculation_metadata", existing_type=sa.JSON(), nullable=False)

    with op.batch_alter_table("assessment_score_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("parent_key", sa.String(length=240), nullable=True))
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("dimension_metadata", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.create_index(batch_op.f("ix_assessment_score_items_parent_key"), ["parent_key"], unique=False)
    with op.batch_alter_table("assessment_score_items", schema=None) as batch_op:
        batch_op.alter_column("sort_order", server_default=None)
        batch_op.alter_column("dimension_metadata", server_default=None)

    with op.batch_alter_table("recommendations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_dimension_type", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("source_dimension_key", sa.String(length=240), nullable=True))
        batch_op.add_column(sa.Column("due_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(batch_op.f("ix_recommendations_is_quick_win"), ["is_quick_win"], unique=False)
        batch_op.create_index(batch_op.f("ix_recommendations_source_dimension_key"), ["source_dimension_key"], unique=False)
        batch_op.create_index(batch_op.f("ix_recommendations_source_dimension_type"), ["source_dimension_type"], unique=False)
        batch_op.create_index(batch_op.f("ix_recommendations_status"), ["status"], unique=False)
        batch_op.create_index(batch_op.f("ix_recommendations_time_horizon"), ["time_horizon"], unique=False)
    with op.batch_alter_table("recommendations", schema=None) as batch_op:
        batch_op.alter_column("sort_order", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("recommendations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recommendations_time_horizon"))
        batch_op.drop_index(batch_op.f("ix_recommendations_status"))
        batch_op.drop_index(batch_op.f("ix_recommendations_source_dimension_type"))
        batch_op.drop_index(batch_op.f("ix_recommendations_source_dimension_key"))
        batch_op.drop_index(batch_op.f("ix_recommendations_is_quick_win"))
        batch_op.drop_column("completed_at")
        batch_op.drop_column("sort_order")
        batch_op.drop_column("due_date")
        batch_op.drop_column("source_dimension_key")
        batch_op.drop_column("source_dimension_type")

    with op.batch_alter_table("assessment_score_items", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_assessment_score_items_parent_key"))
        batch_op.drop_column("dimension_metadata")
        batch_op.drop_column("sort_order")
        batch_op.drop_column("parent_key")

    with op.batch_alter_table("assessment_score_snapshots", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_assessment_score_snapshots_scoring_source"))
        batch_op.drop_index(batch_op.f("ix_assessment_score_snapshots_is_published_snapshot"))
        batch_op.drop_index(batch_op.f("ix_assessment_score_snapshots_input_hash"))
        batch_op.drop_column("calculation_metadata")
        batch_op.drop_column("status_summary")
        batch_op.drop_column("input_hash")
