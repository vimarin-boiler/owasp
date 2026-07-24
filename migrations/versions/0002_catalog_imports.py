"""Add transactional SAMM catalog imports.

Revision ID: 0002_catalog_imports
Revises: 0001_initial
Create Date: 2026-07-24
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_catalog_imports"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_file_hash", sa.String(length=64), nullable=False),
        sa.Column("source_version", sa.String(length=80), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "previewed",
                "invalid",
                "imported",
                "failed",
                name="catalog_import_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("requested_version_name", sa.String(length=180), nullable=True),
        sa.Column("requested_version_number", sa.String(length=80), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("errors_json", sa.JSON(), nullable=False),
        sa.Column("preview_json", sa.JSON(), nullable=False),
        sa.Column("temporary_file_path", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("questionnaire_version_id", sa.Integer(), nullable=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_catalog_imports_created_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["questionnaire_version_id"],
            ["questionnaire_versions.id"],
            name=op.f("fk_catalog_imports_questionnaire_version_id_questionnaire_versions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_imports")),
    )
    with op.batch_alter_table("catalog_imports", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_catalog_imports_created_by_id"), ["created_by_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_catalog_imports_public_id"), ["public_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_catalog_imports_questionnaire_version_id"), ["questionnaire_version_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_catalog_imports_source_file_hash"), ["source_file_hash"], unique=False)
        batch_op.create_index(batch_op.f("ix_catalog_imports_status"), ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("catalog_imports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_catalog_imports_status"))
        batch_op.drop_index(batch_op.f("ix_catalog_imports_source_file_hash"))
        batch_op.drop_index(batch_op.f("ix_catalog_imports_questionnaire_version_id"))
        batch_op.drop_index(batch_op.f("ix_catalog_imports_public_id"))
        batch_op.drop_index(batch_op.f("ix_catalog_imports_created_by_id"))
    op.drop_table("catalog_imports")
