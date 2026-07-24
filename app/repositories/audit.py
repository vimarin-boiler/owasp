from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def recent(self, limit: int = 20) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.actor))
            .order_by(AuditLog.occurred_at.desc())
            .limit(limit)
        )
        return list(db.session.scalars(stmt))


audit_repository = AuditRepository()
