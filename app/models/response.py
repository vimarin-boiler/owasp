from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import ResponseStatus, ReviewDecision
from app.models.base import BaseModel, enum_column, utc_now


class AssessmentResponse(BaseModel):
    __tablename__ = "assessment_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_question_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    respondent_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    selected_option_code: Mapped[str | None] = mapped_column(String(80))
    selected_option_text_snapshot: Mapped[str | None] = mapped_column(Text)
    selected_weight_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    respondent_comment: Mapped[str | None] = mapped_column(Text)
    reviewer_comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ResponseStatus] = mapped_column(
        enum_column(ResponseStatus, "response_status"),
        default=ResponseStatus.UNANSWERED,
        nullable=False,
        index=True,
    )
    is_not_applicable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    not_applicable_justification: Mapped[str | None] = mapped_column(Text)
    response_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    assessment_question: Mapped["AssessmentQuestion"] = relationship(back_populates="response")
    respondent: Mapped["User | None"] = relationship(foreign_keys=[respondent_id])
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewer_id])
    history: Mapped[list["ResponseHistory"]] = relationship(
        back_populates="assessment_response", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="assessment_response", cascade="all, delete-orphan"
    )


class ResponseHistory(BaseModel):
    __tablename__ = "response_history"
    __table_args__ = (
        UniqueConstraint(
            "assessment_response_id", "response_version", name="uq_response_history_version"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_response_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_responses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    response_version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    transition_from: Mapped[str | None] = mapped_column(String(40))
    transition_to: Mapped[str | None] = mapped_column(String(40))
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)

    assessment_response: Mapped[AssessmentResponse] = relationship(back_populates="history")


class Review(BaseModel):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_response_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_responses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    response_version: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision: Mapped[ReviewDecision] = mapped_column(
        enum_column(ReviewDecision, "review_decision"), nullable=False, index=True
    )
    comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    assessment_response: Mapped[AssessmentResponse] = relationship(back_populates="reviews")
    reviewer: Mapped["User"] = relationship()
