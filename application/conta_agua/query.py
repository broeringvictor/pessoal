from dataclasses import dataclass
from core.entities.expenses.conta_agua import ContaAgua
from application.conta_agua.irepository import ContaAguaRepositoryPort
@dataclass(slots=True)
class ContaAguaQuery:
    repositorio: ContaAguaRepositoryPort
    def listar(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
        order_desc: bool = True,
    ) -> list[ContaAgua]:
        return self.repositorio.list(
            offset=offset,
            limit=limit,
            include_deleted=include_deleted,
            order_desc=order_desc,
        )
