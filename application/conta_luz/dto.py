from decimal import Decimal
from pydantic import BaseModel
from core.entities.conta_luz import ContaLuz


class ContaLuzOut(BaseModel):
    referencia: str
    valor: Decimal

    @classmethod
    def from_entity(cls, entidade: ContaLuz) -> "ContaLuzOut":
        return cls(referencia=entidade.referencia, valor=entidade.valor)
