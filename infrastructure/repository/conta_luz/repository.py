from __future__ import annotations

from typing import Iterable, Set, List
from sqlalchemy import select, asc, desc
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
        consulta = select(conta_luz_table.c.referencia).where(
            conta_luz_table.c.deleted_at.is_(None)
        )
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

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> List[ContaLuz]:
        """Lista entidades ContaLuz paginadas, ordenadas por created_at."""
        consulta = select(ContaLuz)
        if not include_deleted:
            consulta = consulta.where(conta_luz_table.c.deleted_at.is_(None))
        ordenacao = (
            desc(conta_luz_table.c.created_at)
            if order_desc
            else asc(conta_luz_table.c.created_at)
        )
        consulta = consulta.order_by(ordenacao).offset(offset).limit(limit)
        resultados = self._session.execute(consulta).scalars().all()
        _logger.debug(
            "Listed ContaLuz entities",
            extra={
                "count": len(resultados),
                "offset": offset,
                "limit": limit,
                "include_deleted": include_deleted,
            },
        )
        return resultados
