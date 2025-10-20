from core.shared.value_objects import ReferenciaMensal, ValorMonetario
from .descricao import Descricao as Description
from .descricao import Descricao
from .mes_referencia import MesReferencia as ReferenceMonth
from .mes_referencia import MesReferencia
from .transaction_type import TransactionType
from .valor import Valor as MonetaryValue
from .valor import Valor
from .evento_data import EventoData as EventDate
from .evento_data import EventoData
from .tipo_despesa import TipoDespesa as ExpenseType
from .tipo_despesa import TipoDespesa

__all__ = [
    # Legacy Portuguese exports
    "ReferenciaMensal",
    "ValorMonetario",
    "MesReferencia",
    "Valor",
    "Descricao",
    "TransactionType",
    "EventoData",
    "TipoDespesa",
    # English aliases
    "ReferenceMonth",
    "MonetaryValue",
    "Description",
    "EventDate",
    "ExpenseType",
]
