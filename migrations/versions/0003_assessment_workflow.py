"""Add assessment workflow notes and evidence review comments.

Revision ID: 0003_assessment_workflow
Revises: 0002_catalog_imports
Create Date: 2026-07-24
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_assessment_workflow"
down_revision: Union[str, None] = "0002_catalog_imports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("evidences", schema=None) as batch_op:
        batch_op.add_column(sa.Column("review_comment", sa.Text(), nullable=True))

    op.create_table(
        "assessment_review_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.id"],
            name=op.f("fk_assessment_review_notes_assessment_id_assessments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            name=op.f("fk_assessment_review_notes_author_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"],
            ["users.id"],
            name=op.f("fk_assessment_review_notes_resolved_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_review_notes")),
    )
    with op.batch_alter_table("assessment_review_notes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_assessment_review_notes_assessment_id"), ["assessment_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_assessment_review_notes_author_id"), ["author_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_assessment_review_notes_is_resolved"), ["is_resolved"], unique=False)
        batch_op.create_index(batch_op.f("ix_assessment_review_notes_public_id"), ["public_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("assessment_review_notes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_assessment_review_notes_public_id"))
        batch_op.drop_index(batch_op.f("ix_assessment_review_notes_is_resolved"))
        batch_op.drop_index(batch_op.f("ix_assessment_review_notes_author_id"))
        batch_op.drop_index(batch_op.f("ix_assessment_review_notes_assessment_id"))
    op.drop_table("assessment_review_notes")

    with op.batch_alter_table("evidences", schema=None) as batch_op:
        batch_op.drop_column("review_comment")
