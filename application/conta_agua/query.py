from dataclasses import dataclass
from typing import Sequence
from core.entities.conta_agua import ContaAgua
from application.conta_agua.interface import ContaAguaRepositoryPort


@dataclass(slots=True)
class ContaAguaQueryService:
    repositorio: ContaAguaRepositoryPort

    def listar(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> Sequence[ContaAgua]:
        return self.repositorio.list(
            offset=offset,
            limit=limit,
            include_deleted=include_deleted,
            order_desc=order_desc,
        )

