from dataclasses import dataclass
from typing import Sequence
from core.entities.conta_luz import ContaLuz
from application.conta_luz.interface import ContaLuzRepositoryPort


@dataclass(slots=True)
class ContaLuzQueryService:
    repositorio: ContaLuzRepositoryPort

    def listar(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> Sequence[ContaLuz]:
        return self.repositorio.list(
            offset=offset,
            limit=limit,
            include_deleted=include_deleted,
            order_desc=order_desc,
        )
