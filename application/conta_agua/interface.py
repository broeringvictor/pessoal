# application/conta_agua/interface.py

from __future__ import annotations

import uuid
from typing import Protocol, Iterable, Sequence, Set

from core.entities.conta_agua import ContaAgua


class ContaAguaRepositoryPort(Protocol):
    """Define o contrato para operações de persistência de ContaAgua."""

    def get_conta_agua(self, conta_agua_id: uuid.UUID) -> ContaAgua | None:
        """
        Busca uma entidade ContaAgua pelo seu ID.

        Retorna:
            A entidade correspondente ou None se não for encontrada.
        """
        ...

    def list_existing_references(self) -> Set[str]:
        """Retorna um conjunto de referências (mm/yyyy) já existentes."""
        ...

    def add_many(self, contas: Iterable[ContaAgua]) -> int:
        """
        Adiciona múltiplas entidades ContaAgua à sessão.

        Retorna:
            O número de entidades adicionadas.
        """
        ...

    def list(
            self,
            *,
            offset: int = 0,
            limit: int = 50,
            include_deleted: bool = False,
            order_desc: bool = True,
    ) -> Sequence[ContaAgua]:
        """Lista entidades ContaAgua com filtros e paginação."""
        ...

    def put(self, conta: ContaAgua) -> ContaAgua:
        """
        Cria uma nova ou atualiza uma entidade ContaAgua existente (upsert).

        Retorna:
            A entidade persistida e gerenciada pela sessão.
        """
        ...