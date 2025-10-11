from typing import Iterable, Protocol, Sequence
from core.entities.conta_luz import ContaLuz


class ContaLuzRepositoryPort(Protocol):
    def list_existing_references(self) -> set[str]: ...

    def add_many(self, contas: Iterable[ContaLuz]) -> int: ...

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> Sequence[ContaLuz]: ...
