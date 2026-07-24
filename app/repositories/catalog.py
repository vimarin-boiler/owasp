from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import (
    AnswerSet,
    BusinessFunction,
    CatalogImport,
    MaturityLevel,
    PracticeStream,
    Question,
    QuestionnaireVersion,
    QuestionnaireVersionQuestion,
    QuestionRevision,
    SecurityPractice,
)


class CatalogRepository:
    def business_functions(self, *, active_only: bool = True) -> list[BusinessFunction]:
        stmt = select(BusinessFunction).options(selectinload(BusinessFunction.practices)).order_by(BusinessFunction.sort_order, BusinessFunction.name)
        if active_only:
            stmt = stmt.where(BusinessFunction.is_active.is_(True))
        return list(db.session.scalars(stmt).unique())

    def business_function_by_public_id(self, public_id: str) -> BusinessFunction | None:
        return db.session.scalar(select(BusinessFunction).where(BusinessFunction.public_id == public_id))

    def security_practices(self, *, active_only: bool = False) -> list[SecurityPractice]:
        stmt = select(SecurityPractice).options(selectinload(SecurityPractice.business_function), selectinload(SecurityPractice.streams)).order_by(SecurityPractice.sort_order, SecurityPractice.name)
        if active_only:
            stmt = stmt.where(SecurityPractice.is_active.is_(True))
        return list(db.session.scalars(stmt).unique())

    def security_practice_by_public_id(self, public_id: str) -> SecurityPractice | None:
        return db.session.scalar(select(SecurityPractice).options(selectinload(SecurityPractice.business_function)).where(SecurityPractice.public_id == public_id))

    def practice_streams(self, *, active_only: bool = False) -> list[PracticeStream]:
        stmt = select(PracticeStream).options(selectinload(PracticeStream.security_practice).selectinload(SecurityPractice.business_function)).order_by(PracticeStream.sort_order, PracticeStream.name)
        if active_only:
            stmt = stmt.where(PracticeStream.is_active.is_(True))
        return list(db.session.scalars(stmt).unique())

    def practice_stream_by_public_id(self, public_id: str) -> PracticeStream | None:
        return db.session.scalar(select(PracticeStream).options(selectinload(PracticeStream.security_practice)).where(PracticeStream.public_id == public_id))

    def maturity_levels(self, *, active_only: bool = False) -> list[MaturityLevel]:
        stmt = select(MaturityLevel).order_by(MaturityLevel.sort_order, MaturityLevel.level_number)
        if active_only:
            stmt = stmt.where(MaturityLevel.is_active.is_(True))
        return list(db.session.scalars(stmt))

    def maturity_level_by_public_id(self, public_id: str) -> MaturityLevel | None:
        return db.session.scalar(select(MaturityLevel).where(MaturityLevel.public_id == public_id))

    def answer_sets(self, *, active_only: bool = False) -> list[AnswerSet]:
        stmt = select(AnswerSet).options(selectinload(AnswerSet.options)).order_by(AnswerSet.name)
        if active_only:
            stmt = stmt.where(AnswerSet.is_active.is_(True))
        return list(db.session.scalars(stmt).unique())

    def answer_set_by_public_id(self, public_id: str) -> AnswerSet | None:
        return db.session.scalar(select(AnswerSet).options(selectinload(AnswerSet.options)).where(AnswerSet.public_id == public_id))

    def questions(self, search: str = "", *, active_only: bool = False) -> list[Question]:
        stmt = select(Question).options(
            selectinload(Question.revisions).selectinload(QuestionRevision.criteria),
            selectinload(Question.revisions).selectinload(QuestionRevision.answer_set).selectinload(AnswerSet.options),
            selectinload(Question.revisions).selectinload(QuestionRevision.business_function),
            selectinload(Question.revisions).selectinload(QuestionRevision.security_practice),
            selectinload(Question.revisions).selectinload(QuestionRevision.practice_stream),
            selectinload(Question.revisions).selectinload(QuestionRevision.maturity_level),
        ).order_by(Question.external_code)
        if active_only:
            stmt = stmt.where(Question.is_active.is_(True))
        if search:
            term = f"%{search}%"
            stmt = stmt.where(or_(Question.external_code.ilike(term), Question.canonical_name.ilike(term)))
        return list(db.session.scalars(stmt).unique())

    def question_by_public_id(self, public_id: str) -> Question | None:
        stmt = (
            select(Question)
            .options(
                selectinload(Question.revisions).selectinload(QuestionRevision.criteria),
                selectinload(Question.revisions).selectinload(QuestionRevision.answer_set).selectinload(AnswerSet.options),
                selectinload(Question.revisions).selectinload(QuestionRevision.business_function),
                selectinload(Question.revisions).selectinload(QuestionRevision.security_practice),
                selectinload(Question.revisions).selectinload(QuestionRevision.practice_stream),
                selectinload(Question.revisions).selectinload(QuestionRevision.maturity_level),
            )
            .where(Question.public_id == public_id)
        )
        return db.session.scalar(stmt)

    def questionnaire_versions(self) -> list[QuestionnaireVersion]:
        stmt = select(QuestionnaireVersion).options(selectinload(QuestionnaireVersion.question_links)).order_by(QuestionnaireVersion.created_at.desc())
        return list(db.session.scalars(stmt).unique())

    def questionnaire_version_by_public_id(self, public_id: str) -> QuestionnaireVersion | None:
        stmt = (
            select(QuestionnaireVersion)
            .options(
                selectinload(QuestionnaireVersion.question_links)
                .selectinload(QuestionnaireVersionQuestion.question_revision)
                .selectinload(QuestionRevision.criteria),
                selectinload(QuestionnaireVersion.question_links)
                .selectinload(QuestionnaireVersionQuestion.question_revision)
                .selectinload(QuestionRevision.answer_set)
                .selectinload(AnswerSet.options),
                selectinload(QuestionnaireVersion.question_links)
                .selectinload(QuestionnaireVersionQuestion.question_revision)
                .selectinload(QuestionRevision.business_function),
                selectinload(QuestionnaireVersion.question_links)
                .selectinload(QuestionnaireVersionQuestion.question_revision)
                .selectinload(QuestionRevision.security_practice),
                selectinload(QuestionnaireVersion.question_links)
                .selectinload(QuestionnaireVersionQuestion.question_revision)
                .selectinload(QuestionRevision.practice_stream),
                selectinload(QuestionnaireVersion.question_links)
                .selectinload(QuestionnaireVersionQuestion.question_revision)
                .selectinload(QuestionRevision.maturity_level),
            )
            .where(QuestionnaireVersion.public_id == public_id)
        )
        return db.session.scalar(stmt)

    def imports(self) -> list[CatalogImport]:
        return list(db.session.scalars(select(CatalogImport).options(selectinload(CatalogImport.questionnaire_version)).order_by(CatalogImport.created_at.desc())))

    def import_by_public_id(self, public_id: str) -> CatalogImport | None:
        return db.session.scalar(select(CatalogImport).options(selectinload(CatalogImport.questionnaire_version)).where(CatalogImport.public_id == public_id))


catalog_repository = CatalogRepository()
