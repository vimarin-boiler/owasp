from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import (
    BusinessFunction,
    Question,
    QuestionnaireVersion,
    QuestionnaireVersionQuestion,
    QuestionRevision,
)
from app.repositories.base import BaseRepository


class CatalogRepository:
    def business_functions(self, *, active_only: bool = True) -> list[BusinessFunction]:
        stmt = select(BusinessFunction).order_by(
            BusinessFunction.sort_order.asc(), BusinessFunction.name.asc()
        )
        if active_only:
            stmt = stmt.where(BusinessFunction.is_active.is_(True))
        return list(db.session.scalars(stmt))

    def question_by_public_id(self, public_id: str) -> Question | None:
        stmt = (
            select(Question)
            .options(
                selectinload(Question.revisions).selectinload(QuestionRevision.criteria),
                selectinload(Question.revisions).selectinload(QuestionRevision.answer_set),
            )
            .where(Question.public_id == public_id)
        )
        return db.session.scalar(stmt)

    def questionnaire_version_by_public_id(
        self, public_id: str
    ) -> QuestionnaireVersion | None:
        stmt = (
            select(QuestionnaireVersion)
            .options(
                selectinload(QuestionnaireVersion.question_links).selectinload(
                    QuestionnaireVersionQuestion.question_revision
                )
            )
            .where(QuestionnaireVersion.public_id == public_id)
        )
        return db.session.scalar(stmt)


catalog_repository = CatalogRepository()
