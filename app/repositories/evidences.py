from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models import Evidence
from app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository[Evidence]):
    model = Evidence

    def get_active_by_public_id(self, public_id: str) -> Evidence | None:
        return db.session.scalar(
            select(Evidence).where(
                Evidence.public_id == public_id,
                Evidence.is_active.is_(True),
            )
        )

    def for_assessment_question(self, assessment_question_id: int) -> list[Evidence]:
        stmt = (
            select(Evidence)
            .where(
                Evidence.assessment_question_id == assessment_question_id,
                Evidence.is_active.is_(True),
            )
            .order_by(Evidence.uploaded_at.desc())
        )
        return list(db.session.scalars(stmt))


evidence_repository = EvidenceRepository()
