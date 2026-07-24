from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import AssessmentResponse, ResponseHistory
from app.repositories.base import BaseRepository


class ResponseRepository(BaseRepository[AssessmentResponse]):
    model = AssessmentResponse

    def get_by_public_id(self, public_id: str) -> AssessmentResponse | None:
        stmt = (
            select(AssessmentResponse)
            .options(
                selectinload(AssessmentResponse.history),
                selectinload(AssessmentResponse.reviews),
            )
            .where(AssessmentResponse.public_id == public_id)
        )
        return db.session.scalar(stmt)

    def for_assessment_question(
        self, assessment_question_id: int
    ) -> AssessmentResponse | None:
        return db.session.scalar(
            select(AssessmentResponse).where(
                AssessmentResponse.assessment_question_id == assessment_question_id
            )
        )

    def history(self, assessment_response_id: int) -> list[ResponseHistory]:
        stmt = (
            select(ResponseHistory)
            .where(ResponseHistory.assessment_response_id == assessment_response_id)
            .order_by(ResponseHistory.response_version.desc())
        )
        return list(db.session.scalars(stmt))


response_repository = ResponseRepository()
