"""Generic repository.

Repository pattern: services depend on these classes instead of touching
SQLAlchemy queries directly, which keeps the business tier testable and makes
the data tier swappable.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    # ---- writes -----------------------------------------------------------
    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.flush()  # assigns the PK without ending the transaction
        return entity

    def create(self, **fields: Any) -> ModelT:
        return self.add(self.model(**fields))

    def delete(self, entity: ModelT) -> None:
        self.db.delete(entity)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    # ---- reads ------------------------------------------------------------
    def get(self, entity_id: uuid.UUID | str) -> ModelT | None:
        return self.db.get(self.model, entity_id)

    def list_all(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars())

    def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return int(self.db.execute(stmt).scalar_one())
