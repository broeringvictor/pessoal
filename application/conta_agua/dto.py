from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel
from core.entities.conta_agua import ContaAgua


class ContaAguaOut(BaseModel):
    referencia: str
    valor: Decimal

    @classmethod
    def from_entity(cls, entidade: ContaAgua) -> "ContaAguaOut":
        return cls(referencia=entidade.referencia, valor=entidade.valor)

