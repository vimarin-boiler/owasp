from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Role, User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email_normalized: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.role_links).selectinload(UserRole.role))
            .where(User.email_normalized == email_normalized)
        )
        return db.session.scalar(stmt)

    def get_by_public_id(self, public_id: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.role_links).selectinload(UserRole.role))
            .where(User.public_id == public_id)
        )
        return db.session.scalar(stmt)

    def list(self, search: str | None = None) -> list[User]:
        stmt = select(User).options(
            selectinload(User.role_links).selectinload(UserRole.role)
        )
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(User.display_name.ilike(pattern), User.email.ilike(pattern))
            )
        stmt = stmt.order_by(User.display_name.asc())
        return list(db.session.scalars(stmt).unique())

    def count_active(self) -> int:
        return int(
            db.session.scalar(select(func.count(User.id)).where(User.is_active.is_(True)))
            or 0
        )

    def roles(self) -> list[Role]:
        return list(
            db.session.scalars(
                select(Role).where(Role.is_active.is_(True)).order_by(Role.name.asc())
            )
        )

    def roles_by_ids(self, role_ids: list[int]) -> list[Role]:
        if not role_ids:
            return []
        return list(db.session.scalars(select(Role).where(Role.id.in_(role_ids))))


user_repository = UserRepository()
