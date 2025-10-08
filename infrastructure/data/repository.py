from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from core.entities.conta_luz import ContaLuz
from core.entities.conta_agua import ContaAgua


class ContaLuzRepository:
    """Repository for ContaLuz using SQLAlchemy Session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ContaLuz) -> ContaLuz:
        self._session.add(entity)
        return entity

    def get_by_id(self, entity_id: UUID) -> Optional[ContaLuz]:
        return self._session.get(ContaLuz, entity_id)

    def list_all(self) -> Iterable[ContaLuz]:
        return self._session.query(ContaLuz).all()

    def delete(self, entity: ContaLuz) -> None:
        entity.deleted_at = entity.deleted_at or None  # domain may set timestamp separately
        self._session.delete(entity)


class ContaAguaRepository:
    """Repository for ContaAgua using SQLAlchemy Session."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ContaAgua) -> ContaAgua:
        self._session.add(entity)
        return entity

    def get_by_id(self, entity_id: UUID) -> Optional[ContaAgua]:
        return self._session.get(ContaAgua, entity_id)

    def list_all(self) -> Iterable[ContaAgua]:
        return self._session.query(ContaAgua).all()

    def delete(self, entity: ContaAgua) -> None:
        entity.deleted_at = entity.deleted_at or None
        self._session.delete(entity)

