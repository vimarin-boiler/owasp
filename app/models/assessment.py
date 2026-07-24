from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import AssessmentStatus, AssignmentRole, ResponseStatus, ScoringSource
from app.models.base import ActorAuditMixin, BaseModel, enum_column, utc_now


class Assessment(BaseModel, ActorAuditMixin):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    questionnaire_version_id: Mapped[int] = mapped_column(
        ForeignKey("questionnaire_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    target_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[AssessmentStatus] = mapped_column(
        enum_column(AssessmentStatus, "assessment_status"),
        default=AssessmentStatus.DRAFT,
        nullable=False,
        index=True,
    )
    target_maturity_level: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    scoring_source: Mapped[ScoringSource] = mapped_column(
        enum_column(ScoringSource, "assessment_scoring_source"),
        default=ScoringSource.APPROVED,
        nullable=False,
    )
    results_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settings_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="assessments")
    questionnaire_version: Mapped["QuestionnaireVersion"] = relationship()
    assignments: Mapped[list["AssessmentUser"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    questions: Mapped[list["AssessmentQuestion"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentQuestion.sort_order"
    )
    review_notes: Mapped[list["AssessmentReviewNote"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by=lambda: AssessmentReviewNote.created_at.desc()
    )


class AssessmentUser(BaseModel):
    __tablename__ = "assessment_users"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "user_id", "assignment_role", name="uq_assessment_users_assignment"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignment_role: Mapped[AssignmentRole] = mapped_column(
        enum_column(AssignmentRole, "assignment_role"), nullable=False
    )
    is_lead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    assigned_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    assessment: Mapped[Assessment] = relationship(back_populates="assignments")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    assigned_by: Mapped["User | None"] = relationship(foreign_keys=[assigned_by_id])


class AssessmentQuestion(BaseModel):
    __tablename__ = "assessment_questions"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id", "source_question_revision_id", name="uq_assessment_question_source"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_question_revision_id: Mapped[int] = mapped_column(
        ForeignKey("question_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    external_code_snapshot: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    question_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    guidance_snapshot: Mapped[str | None] = mapped_column(Text)
    criteria_snapshot: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    answer_options_snapshot: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    business_function_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    security_practice_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    practice_stream_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    maturity_level_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_status: Mapped[ResponseStatus] = mapped_column(
        enum_column(ResponseStatus, "assessment_question_status"),
        default=ResponseStatus.UNANSWERED,
        nullable=False,
        index=True,
    )

    assessment: Mapped[Assessment] = relationship(back_populates="questions")
    source_question_revision: Mapped["QuestionRevision"] = relationship()
    response: Mapped["AssessmentResponse | None"] = relationship(
        back_populates="assessment_question", uselist=False, cascade="all, delete-orphan"
    )
    evidences: Mapped[list["Evidence"]] = relationship(
        back_populates="assessment_question", cascade="all, delete-orphan"
    )


class AssessmentReviewNote(BaseModel):
    __tablename__ = "assessment_review_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    assessment: Mapped[Assessment] = relationship(back_populates="review_notes")
    author: Mapped["User"] = relationship(foreign_keys=[author_id])
    resolved_by: Mapped["User | None"] = relationship(foreign_keys=[resolved_by_id])
