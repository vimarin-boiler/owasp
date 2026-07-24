from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import ScoringSource
from app.models.base import BaseModel, enum_column, utc_now


class AssessmentScoreSnapshot(BaseModel):
    __tablename__ = "assessment_score_snapshots"
    __table_args__ = (
        UniqueConstraint("assessment_id", "snapshot_number", name="uq_score_snapshot_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    scoring_source: Mapped[ScoringSource] = mapped_column(
        enum_column(ScoringSource, "score_snapshot_source"), nullable=False, index=True
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    calculated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    overall_score: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    progress_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(40), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    calculation_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_published_snapshot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    assessment: Mapped["Assessment"] = relationship()
    calculated_by: Mapped["User | None"] = relationship()
    items: Mapped[list["AssessmentScoreItem"]] = relationship(
        back_populates="score_snapshot", cascade="all, delete-orphan", order_by="AssessmentScoreItem.sort_order"
    )


class AssessmentScoreItem(BaseModel):
    __tablename__ = "assessment_score_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    score_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_score_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dimension_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    dimension_key: Mapped[str] = mapped_column(String(240), nullable=False)
    dimension_name: Mapped[str] = mapped_column(String(240), nullable=False)
    parent_key: Mapped[str | None] = mapped_column(String(240), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dimension_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    normalized_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    target_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    gap: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    applicable_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_applicable_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    score_snapshot: Mapped[AssessmentScoreSnapshot] = relationship(back_populates="items")
