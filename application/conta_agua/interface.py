from typing import Iterable, Protocol, Sequence
from core.entities.conta_agua import ContaAgua


class ContaAguaRepositoryPort(Protocol):
    def list_existing_references(self) -> set[str]: ...

    def add_many(self, contas: Iterable[ContaAgua]) -> int: ...

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> Sequence[ContaAgua]: ...

