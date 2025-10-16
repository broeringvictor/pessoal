
from enum import Enum


class ETransaction(Enum):
    """Enumeração para categorizar transações financeiras."""
    ENTRADA = 1
    SAIDA = 2
    TRANSFERENCIA = 3
    INVESTIMENTO = 4
