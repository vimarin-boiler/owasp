from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Organization, OrganizationMembership
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    def get_by_slug(self, slug: str) -> Organization | None:
        return db.session.scalar(select(Organization).where(Organization.slug == slug))

    def get_by_public_id(self, public_id: str) -> Organization | None:
        stmt = (
            select(Organization)
            .options(selectinload(Organization.memberships))
            .where(Organization.public_id == public_id)
        )
        return db.session.scalar(stmt)

    def list(self, search: str | None = None) -> list[Organization]:
        stmt = select(Organization)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Organization.name.ilike(pattern),
                    Organization.legal_name.ilike(pattern),
                    Organization.tax_identifier.ilike(pattern),
                )
            )
        stmt = stmt.order_by(Organization.name.asc())
        return list(db.session.scalars(stmt))

    def count_active(self) -> int:
        return int(
            db.session.scalar(
                select(func.count(Organization.id)).where(
                    Organization.is_active.is_(True)
                )
            )
            or 0
        )


organization_repository = OrganizationRepository()
