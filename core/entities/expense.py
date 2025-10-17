from dataclasses import dataclass

from core.shared.entities import Entity
from core.value_object import Descricao, Valor, TipoDespesa


@dataclass(slots=True, init=False)
class Expense(Entity):
    """Entidade de despesa genérica."""
    description: Descricao
    amount: Valor
    expense_type: TipoDespesa
    
    