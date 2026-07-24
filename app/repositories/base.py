from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select

from app.extensions import db

T = TypeVar("T")


class BaseRepository(Generic[T]):
    model: type[T]

    def get_by_public_id(self, public_id: str) -> T | None:
        return db.session.scalar(select(self.model).where(self.model.public_id == public_id))

    def add(self, entity: T) -> T:
        db.session.add(entity)
        return entity

    def deactivate(self, entity: T) -> None:
        deactivate = getattr(entity, "deactivate", None)
        if deactivate is None:
            raise TypeError(f"{type(entity).__name__} no admite desactivación lógica.")
        deactivate()
