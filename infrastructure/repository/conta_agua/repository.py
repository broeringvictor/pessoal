from __future__ import annotations

from typing import Iterable, Set, List
from sqlalchemy import select, asc, desc
from sqlalchemy.orm import Session
import logging

from core.entities.conta_agua import ContaAgua
from infrastructure.data.mappings import conta_agua_table

_logger = logging.getLogger("pessoal.infrastructure.repository.conta_agua")


class ContaAguaRepository:
    """Repositório de persistência para ContaAgua baseado em SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_existing_references(self) -> Set[str]:
        """Retorna conjunto de referências (mm/yyyy) já persistidas (não deletadas)."""
        consulta = select(conta_agua_table.c.referencia_data).where(
            conta_agua_table.c.deleted_at.is_(None)
        )
        datas = self._session.execute(consulta).scalars().all()
        referencias = {f"{d.month:02d}/{d.year}" for d in datas}
        _logger.info("Fetched water references", extra={"count": len(referencias)})
        return referencias

    def add_many(self, contas: Iterable[ContaAgua]) -> int:
        inseridos = 0
        for entidade in contas:
            self._session.add(entidade)
            inseridos += 1
        _logger.info("Queued water entities to insert", extra={"count": inseridos})
        return inseridos

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> List[ContaAgua]:
        consulta = select(ContaAgua)
        if not include_deleted:
            consulta = consulta.where(conta_agua_table.c.deleted_at.is_(None))
        ordenacao = (
            desc(conta_agua_table.c.created_at)
            if order_desc
            else asc(conta_agua_table.c.created_at)
        )
        consulta = consulta.order_by(ordenacao).offset(offset).limit(limit)
        resultados = self._session.execute(consulta).scalars().all()
        _logger.debug(
            "Listed ContaAgua entities",
            extra={
                "count": len(resultados),
                "offset": offset,
                "limit": limit,
                "include_deleted": include_deleted,
            },
        )
        return resultados

