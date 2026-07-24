from __future__ import annotations

from sqlalchemy import case, select
from sqlalchemy.orm import selectinload

from app.enums import RecommendationPriority, RecommendationStatus
from app.extensions import db
from app.models import Recommendation
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation

    @staticmethod
    def _options():
        return (
            selectinload(Recommendation.assessment),
            selectinload(Recommendation.business_function),
            selectinload(Recommendation.security_practice),
            selectinload(Recommendation.practice_stream),
            selectinload(Recommendation.assessment_question),
        )

    def get_for_assessment(self, assessment_id: int, public_id: str) -> Recommendation | None:
        return db.session.scalar(
            select(Recommendation)
            .options(*self._options())
            .where(
                Recommendation.assessment_id == assessment_id,
                Recommendation.public_id == public_id,
            )
        )

    def for_assessment(
        self,
        assessment_id: int,
        *,
        active_only: bool = True,
        priority: RecommendationPriority | None = None,
        status: RecommendationStatus | None = None,
    ) -> list[Recommendation]:
        priority_order = case(
            (Recommendation.priority == RecommendationPriority.CRITICAL, 1),
            (Recommendation.priority == RecommendationPriority.HIGH, 2),
            (Recommendation.priority == RecommendationPriority.MEDIUM, 3),
            else_=4,
        )
        stmt = (
            select(Recommendation)
            .options(*self._options())
            .where(Recommendation.assessment_id == assessment_id)
        )
        if active_only:
            stmt = stmt.where(Recommendation.is_active.is_(True))
        if priority is not None:
            stmt = stmt.where(Recommendation.priority == priority)
        if status is not None:
            stmt = stmt.where(Recommendation.status == status)
        stmt = stmt.order_by(priority_order, Recommendation.sort_order, Recommendation.created_at)
        return list(db.session.scalars(stmt).unique())


recommendation_repository = RecommendationRepository()
