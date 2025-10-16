# infrastructure/repository/conta_agua_endpoints.py
from __future__ import annotations
import logging
import uuid
from typing import Iterable
from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session
from application.conta_agua.irepository import ContaAguaRepositoryPort
from core.entities.conta_agua import ContaAgua
from infrastructure.data.mappings import conta_agua_table
_logger = logging.getLogger("pessoal.infrastructure.repository.conta_agua")
class ContaAguaRepository(ContaAguaRepositoryPort):
    """Repositório de persistência para ContaAgua baseado em SQLAlchemy."""
    def __init__(self, session: Session) -> None:
        self._session = session
    def get_conta_agua(self, conta_agua_id: uuid.UUID) -> ContaAgua | None:
        # Seleciona a entidade completa e retorna None quando não encontrada
        consulta = (
            select(ContaAgua)
            .where(ContaAgua.id == conta_agua_id)
            .where(conta_agua_table.c.deleted_at.is_(None))
        )
        return self._session.execute(consulta).scalar_one_or_none()
    def list_existing_references(self) -> set[str]:
        """Retorna conjunto de referências (mm/yyyy) já persistidas (não deletadas)."""
        consulta = select(conta_agua_table.c.referencia_data).where(
            conta_agua_table.c.deleted_at.is_(None)
        )
        datas = self._session.execute(consulta).scalars().all()
        referencias = {f"{d.month:02d}/{d.year}" for d in datas}
        _logger.info("Fetched water references", extra={"count": len(referencias)})
        return referencias
    def add_many(self, contas: Iterable[ContaAgua]) -> int:
        # Utiliza session.add_all() para operação em lote
        contas_list = list(contas)
        self._session.add_all(contas_list)
        count = len(contas_list)
        _logger.info("Queued water entities to insert", extra={"count": count})
        return count
    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> list[ContaAgua]:
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
    def put(self, conta: ContaAgua) -> ContaAgua:
        # Upsert idempotente via merge
        merged_conta = self._session.merge(conta)
        _logger.info("Queued water entity for upsert", extra={"id": merged_conta.id})
        return merged_conta
