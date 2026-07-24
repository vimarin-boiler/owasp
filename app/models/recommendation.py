from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import RecommendationPriority, RecommendationStatus
from app.models.base import ActorAuditMixin, BaseModel, SoftDeleteMixin, enum_column


class Recommendation(BaseModel, ActorAuditMixin, SoftDeleteMixin):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    business_function_id: Mapped[int | None] = mapped_column(
        ForeignKey("business_functions.id", ondelete="SET NULL")
    )
    security_practice_id: Mapped[int | None] = mapped_column(
        ForeignKey("security_practices.id", ondelete="SET NULL")
    )
    practice_stream_id: Mapped[int | None] = mapped_column(
        ForeignKey("practice_streams.id", ondelete="SET NULL")
    )
    assessment_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("assessment_questions.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    risk: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[RecommendationPriority] = mapped_column(
        enum_column(RecommendationPriority, "recommendation_priority"), nullable=False, index=True
    )
    effort: Mapped[str | None] = mapped_column(String(80))
    suggested_owner: Mapped[str | None] = mapped_column(String(180))
    time_horizon: Mapped[str | None] = mapped_column(String(80))
    dependencies: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RecommendationStatus] = mapped_column(
        enum_column(RecommendationStatus, "recommendation_status"),
        default=RecommendationStatus.OPEN,
        nullable=False,
    )
    is_quick_win: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    target_maturity_level: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    assessment: Mapped["Assessment"] = relationship()
