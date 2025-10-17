from __future__ import annotations
import uuid
from typing import Protocol, Iterable
from core.entities.expenses.conta_agua import ContaAgua
class ContaAguaRepositoryPort(Protocol):
    """Contrato de persistência para operações de ContaAgua (DI)."""
    def get_conta_agua(self, conta_agua_id: uuid.UUID) -> ContaAgua | None: ...
    def list_existing_references(self) -> set[str]: ...
    def add_many(self, contas: Iterable[ContaAgua]) -> int: ...
    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> list[ContaAgua]: ...
    def put(self, conta: ContaAgua) -> ContaAgua: ...
