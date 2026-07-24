from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models import Recommendation
from app.repositories.base import BaseRepository


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation

    def for_assessment(
        self, assessment_id: int, *, active_only: bool = True
    ) -> list[Recommendation]:
        stmt = select(Recommendation).where(
            Recommendation.assessment_id == assessment_id
        )
        if active_only:
            stmt = stmt.where(Recommendation.is_active.is_(True))
        stmt = stmt.order_by(
            Recommendation.priority.asc(), Recommendation.created_at.asc()
        )
        return list(db.session.scalars(stmt))


recommendation_repository = RecommendationRepository()
