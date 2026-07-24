from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Assessment, AssessmentQuestion, AssessmentUser
from app.repositories.base import BaseRepository


class AssessmentRepository(BaseRepository[Assessment]):
    model = Assessment

    def get_by_public_id(self, public_id: str) -> Assessment | None:
        stmt = (
            select(Assessment)
            .options(
                selectinload(Assessment.assignments),
                selectinload(Assessment.questions),
            )
            .where(Assessment.public_id == public_id)
        )
        return db.session.scalar(stmt)

    def for_user(self, user_id: int) -> list[Assessment]:
        stmt = (
            select(Assessment)
            .join(AssessmentUser, AssessmentUser.assessment_id == Assessment.id)
            .where(AssessmentUser.user_id == user_id)
            .order_by(Assessment.target_date.asc(), Assessment.created_at.desc())
        )
        return list(db.session.scalars(stmt).unique())

    def question_by_public_id(
        self, assessment_id: int, question_public_id: str
    ) -> AssessmentQuestion | None:
        stmt = select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == assessment_id,
            AssessmentQuestion.public_id == question_public_id,
        )
        return db.session.scalar(stmt)


assessment_repository = AssessmentRepository()
