from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import CatalogImportStatus, QuestionRevisionStatus, QuestionnaireStatus
from app.models.base import ActorAuditMixin, BaseModel, SoftDeleteMixin, enum_column


class BusinessFunction(BaseModel, ActorAuditMixin, SoftDeleteMixin):
    __tablename__ = "business_functions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    practices: Mapped[list["SecurityPractice"]] = relationship(
        back_populates="business_function"
    )


class SecurityPractice(BaseModel, ActorAuditMixin, SoftDeleteMixin):
    __tablename__ = "security_practices"
    __table_args__ = (
        UniqueConstraint(
            "business_function_id", "code", name="uq_security_practices_function_code"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_function_id: Mapped[int] = mapped_column(
        ForeignKey("business_functions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    business_function: Mapped[BusinessFunction] = relationship(back_populates="practices")
    streams: Mapped[list["PracticeStream"]] = relationship(back_populates="security_practice")


class PracticeStream(BaseModel, ActorAuditMixin, SoftDeleteMixin):
    __tablename__ = "practice_streams"
    __table_args__ = (
        UniqueConstraint(
            "security_practice_id", "code", name="uq_practice_streams_practice_code"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    security_practice_id: Mapped[int] = mapped_column(
        ForeignKey("security_practices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    security_practice: Mapped[SecurityPractice] = relationship(back_populates="streams")


class MaturityLevel(BaseModel, ActorAuditMixin, SoftDeleteMixin):
    __tablename__ = "maturity_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    level_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    max_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("1.0"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class AnswerSet(BaseModel, ActorAuditMixin, SoftDeleteMixin):
    __tablename__ = "answer_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    options: Mapped[list["AnswerOption"]] = relationship(
        back_populates="answer_set", cascade="all, delete-orphan", order_by="AnswerOption.sort_order"
    )


class AnswerOption(BaseModel, ActorAuditMixin, SoftDeleteMixin):
    __tablename__ = "answer_options"
    __table_args__ = (
        UniqueConstraint(
            "answer_set_id", "option_code", name="uq_answer_options_set_code"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_set_id: Mapped[int] = mapped_column(
        ForeignKey("answer_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_code: Mapped[str] = mapped_column(String(80), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    answer_set: Mapped[AnswerSet] = relationship(back_populates="options")


class Question(BaseModel, ActorAuditMixin, SoftDeleteMixin):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    canonical_name: Mapped[str | None] = mapped_column(String(240))
    current_revision_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    revisions: Mapped[list["QuestionRevision"]] = relationship(
        back_populates="question",
        foreign_keys="QuestionRevision.question_id",
        cascade="all, delete-orphan",
    )

    @property
    def current_revision(self) -> "QuestionRevision | None":
        if self.current_revision_number is None:
            return None
        return next(
            (revision for revision in self.revisions if revision.revision_number == self.current_revision_number),
            None,
        )


class QuestionRevision(BaseModel, ActorAuditMixin):
    __tablename__ = "question_revisions"
    __table_args__ = (
        UniqueConstraint(
            "question_id", "revision_number", name="uq_question_revisions_question_number"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    business_function_id: Mapped[int] = mapped_column(
        ForeignKey("business_functions.id", ondelete="RESTRICT"), nullable=False
    )
    security_practice_id: Mapped[int] = mapped_column(
        ForeignKey("security_practices.id", ondelete="RESTRICT"), nullable=False
    )
    practice_stream_id: Mapped[int] = mapped_column(
        ForeignKey("practice_streams.id", ondelete="RESTRICT"), nullable=False
    )
    maturity_level_id: Mapped[int] = mapped_column(
        ForeignKey("maturity_levels.id", ondelete="RESTRICT"), nullable=False
    )
    answer_set_id: Mapped[int] = mapped_column(
        ForeignKey("answer_sets.id", ondelete="RESTRICT"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    guidance_text: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    supersedes_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("question_revisions.id", ondelete="SET NULL")
    )
    change_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[QuestionRevisionStatus] = mapped_column(
        enum_column(QuestionRevisionStatus, "question_revision_status"),
        default=QuestionRevisionStatus.DRAFT,
        nullable=False,
    )

    question: Mapped[Question] = relationship(
        back_populates="revisions", foreign_keys=[question_id]
    )
    criteria: Mapped[list["QuestionQualityCriterion"]] = relationship(
        back_populates="question_revision",
        cascade="all, delete-orphan",
        order_by="QuestionQualityCriterion.sort_order",
    )
    answer_set: Mapped[AnswerSet] = relationship()
    business_function: Mapped[BusinessFunction] = relationship()
    security_practice: Mapped[SecurityPractice] = relationship()
    practice_stream: Mapped[PracticeStream] = relationship()
    maturity_level: Mapped[MaturityLevel] = relationship()


class QuestionQualityCriterion(BaseModel, ActorAuditMixin):
    __tablename__ = "question_quality_criteria"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_revision_id: Mapped[int] = mapped_column(
        ForeignKey("question_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criterion_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question_revision: Mapped[QuestionRevision] = relationship(back_populates="criteria")


class QuestionnaireVersion(BaseModel, ActorAuditMixin):
    __tablename__ = "questionnaire_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    version_number: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[QuestionnaireStatus] = mapped_column(
        enum_column(QuestionnaireStatus, "questionnaire_status"),
        default=QuestionnaireStatus.DRAFT,
        nullable=False,
    )
    source_name: Mapped[str | None] = mapped_column(String(255))
    source_file_hash: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    question_links: Mapped[list["QuestionnaireVersionQuestion"]] = relationship(
        back_populates="questionnaire_version", cascade="all, delete-orphan"
    )


class QuestionnaireVersionQuestion(BaseModel):
    __tablename__ = "questionnaire_version_questions"
    __table_args__ = (
        UniqueConstraint(
            "questionnaire_version_id",
            "question_revision_id",
            name="uq_questionnaire_version_revision",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    questionnaire_version_id: Mapped[int] = mapped_column(
        ForeignKey("questionnaire_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_revision_id: Mapped[int] = mapped_column(
        ForeignKey("question_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weight_override: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    questionnaire_version: Mapped[QuestionnaireVersion] = relationship(
        back_populates="question_links"
    )
    question_revision: Mapped[QuestionRevision] = relationship()


class CatalogImport(BaseModel):
    __tablename__ = "catalog_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[CatalogImportStatus] = mapped_column(
        enum_column(CatalogImportStatus, "catalog_import_status"),
        default=CatalogImportStatus.PREVIEWED,
        nullable=False,
        index=True,
    )
    requested_version_name: Mapped[str | None] = mapped_column(String(180))
    requested_version_number: Mapped[str | None] = mapped_column(String(80))
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    errors_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    preview_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    temporary_file_path: Mapped[str | None] = mapped_column(String(500))
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    questionnaire_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("questionnaire_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    questionnaire_version: Mapped[QuestionnaireVersion | None] = relationship()
