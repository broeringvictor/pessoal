from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Union

from core.shared.entities import Entity
from core.value_object import Descricao, Valor, TipoDespesa


@dataclass(slots=True, init=False)
class Expense(Entity):
    """Entidade de despesa genérica base para a hierarquia de despesas."""
    description: Descricao
    amount: Valor
    expense_type: TipoDespesa

    def __init__(
        self,
        *,
        description: Descricao,
        amount: Union[Valor, str, int, float, Decimal],
        expense_type: TipoDespesa,
    ) -> None:
        self.description = description
        self.amount = self._normalizar_valor(amount)
        self.expense_type = expense_type
        Entity.__post_init__(self)

    @staticmethod
    def _normalizar_valor(valor: Union[Valor, str, int, float, Decimal]) -> Valor:
        # Converte dados brutos para VO Valor quando necessário
        if isinstance(valor, Valor):
            return valor
        return Valor.criar_de_bruto(valor)

    # ----------------- Fábrica (Create) -----------------
    @classmethod
    def criar(
        cls,
        *,
        description: Descricao,
        amount: Union[Valor, str, int, float, Decimal],
        expense_type: TipoDespesa,
    ) -> "Expense":
        return cls(description=description, amount=amount, expense_type=expense_type)

    # ----------------- Atualização Completa (Update) -----------------
    def atualizar(
        self,
        *,
        description: Descricao,
        amount: Union[Valor, str, int, float, Decimal],
        expense_type: TipoDespesa,
    ) -> "Expense":
        self.description = description
        self.amount = self._normalizar_valor(amount)
        self.expense_type = expense_type
        self.registrar_atualizacao()
        return self

    # ----------------- Atualização Parcial (Patch) -----------------
    def patch(
        self,
        *,
        description: Optional[Descricao] = None,
        amount: Optional[Union[Valor, str, int, float, Decimal]] = None,
        expense_type: Optional[TipoDespesa] = None,
    ) -> "Expense":
        houve_alteracao = False
        if description is not None:
            self.description = description
            houve_alteracao = True
        if amount is not None:
            self.amount = self._normalizar_valor(amount)
            houve_alteracao = True
        if expense_type is not None:
            self.expense_type = expense_type
            houve_alteracao = True

        if houve_alteracao:
            self.registrar_atualizacao()
        return self

    # ----------------- Exclusão Lógica (Soft Delete) -----------------
    def deletar(self) -> None:
        self.registrar_exclusao()
