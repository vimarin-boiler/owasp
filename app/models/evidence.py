from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import EvidenceValidationStatus
from app.models.base import BaseModel, SoftDeleteMixin, enum_column, utc_now


class Evidence(BaseModel, SoftDeleteMixin):
    __tablename__ = "evidences"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_question_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_response_id: Mapped[int | None] = mapped_column(
        ForeignKey("assessment_responses.id", ondelete="SET NULL"), index=True
    )
    response_version: Mapped[int | None] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    internal_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    reported_mime_type: Mapped[str | None] = mapped_column(String(160))
    detected_mime_type: Mapped[str | None] = mapped_column(String(160))
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    uploaded_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    validation_status: Mapped[EvidenceValidationStatus] = mapped_column(
        enum_column(EvidenceValidationStatus, "evidence_validation_status"),
        default=EvidenceValidationStatus.PENDING,
        nullable=False,
        index=True,
    )
    review_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assessment_question: Mapped["AssessmentQuestion"] = relationship(back_populates="evidences")
    assessment_response: Mapped["AssessmentResponse | None"] = relationship()
    uploaded_by: Mapped["User"] = relationship(foreign_keys=[uploaded_by_id])
    reviewed_by: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by_id])
