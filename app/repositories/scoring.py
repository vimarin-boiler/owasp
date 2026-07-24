from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.enums import ScoringSource
from app.extensions import db
from app.models import AssessmentScoreSnapshot
from app.repositories.base import BaseRepository


class ScoringRepository(BaseRepository[AssessmentScoreSnapshot]):
    model = AssessmentScoreSnapshot

    def latest(self, assessment_id: int, source: ScoringSource | None = None) -> AssessmentScoreSnapshot | None:
        stmt = (
            select(AssessmentScoreSnapshot)
            .options(selectinload(AssessmentScoreSnapshot.items))
            .where(AssessmentScoreSnapshot.assessment_id == assessment_id)
        )
        if source is not None:
            stmt = stmt.where(AssessmentScoreSnapshot.scoring_source == source)
        stmt = stmt.order_by(AssessmentScoreSnapshot.snapshot_number.desc()).limit(1)
        return db.session.scalar(stmt)

    def published(self, assessment_id: int) -> AssessmentScoreSnapshot | None:
        stmt = (
            select(AssessmentScoreSnapshot)
            .options(selectinload(AssessmentScoreSnapshot.items))
            .where(
                AssessmentScoreSnapshot.assessment_id == assessment_id,
                AssessmentScoreSnapshot.is_published_snapshot.is_(True),
            )
            .order_by(AssessmentScoreSnapshot.snapshot_number.desc())
            .limit(1)
        )
        return db.session.scalar(stmt)

    def next_number(self, assessment_id: int) -> int:
        value = db.session.scalar(
            select(func.max(AssessmentScoreSnapshot.snapshot_number)).where(
                AssessmentScoreSnapshot.assessment_id == assessment_id
            )
        )
        return int(value or 0) + 1

    def history(self, assessment_id: int, limit: int = 20) -> list[AssessmentScoreSnapshot]:
        stmt = (
            select(AssessmentScoreSnapshot)
            .where(AssessmentScoreSnapshot.assessment_id == assessment_id)
            .order_by(AssessmentScoreSnapshot.snapshot_number.desc())
            .limit(limit)
        )
        return list(db.session.scalars(stmt))


scoring_repository = ScoringRepository()
