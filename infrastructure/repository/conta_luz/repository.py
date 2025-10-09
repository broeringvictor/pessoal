from __future__ import annotations

from typing import Iterable, Set
from sqlalchemy import select
from sqlalchemy.orm import Session
import logging

from core.entities.conta_luz import ContaLuz
from infrastructure.data.mappings import conta_luz_table

_logger = logging.getLogger("pessoal.infrastructure.repository.conta_luz")


class ContaLuzRepository:
    """Repositório de persistência para ContaLuz baseado em SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_existing_references(self) -> Set[str]:
        """Retorna um conjunto de referências (mm/yyyy) já persistidas (não deletadas)."""
        consulta = select(conta_luz_table.c.referencia).where(conta_luz_table.c.deleted_at.is_(None))
        resultados = self._session.execute(consulta).scalars().all()
        referencias = set(str(valor) for valor in resultados)
        _logger.info("Fetched existing references", extra={"count": len(referencias)})
        return referencias

    def add_many(self, contas: Iterable[ContaLuz]) -> int:
        """Adiciona várias entidades ContaLuz e retorna a quantidade inserida."""
        contador_inseridos = 0
        for entidade in contas:
            self._session.add(entidade)
            contador_inseridos += 1
        _logger.info("Queued entities to insert", extra={"count": contador_inseridos})
        return contador_inseridos
