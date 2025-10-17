from __future__ import annotations

from typing import Protocol, Iterable
from core.entities.expenses.conta_luz import ContaLuz


class ContaLuzRepositoryPort(Protocol):
    """Contrato de persistência para operações de ContaLuz (DI)."""

    def list_existing_references(self) -> set[str]: ...

    def add_many(self, contas: Iterable[ContaLuz]) -> int: ...

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> list[ContaLuz]: ...

    def put(self, conta: ContaLuz) -> ContaLuz: ...
