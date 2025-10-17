from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel

from application.shared.response import Response
from core.entities.expenses.conta_luz import ContaLuz


class ContaLuzOut(BaseModel):
    referencia: str
    valor: Decimal

    @classmethod
    def from_entity(cls, entidade: ContaLuz) -> "ContaLuzOut":
        return cls(referencia=entidade.referencia, valor=entidade.valor)

    @classmethod
    def sucesso_de_entidade(
        cls,
        entidade: ContaLuz,
        mensagem: str = "Conta de luz obtida com sucesso",
        codigo: int = 200,
    ) -> Response:
        return Response.sucesso(data=cls.from_entity(entidade).model_dump(), message=mensagem, code=codigo)

    @classmethod
    def sucesso_de_lista(
        cls,
        entidades: list[ContaLuz],
        mensagem: str = "Contas de luz obtidas com sucesso",
        codigo: int = 200,
    ) -> Response:
        payload = [cls.from_entity(entidade).model_dump() for entidade in entidades]
        return Response.sucesso(data=payload, message=mensagem, code=codigo)

    @classmethod
    def response_importacao(
        cls,
        entidades: list[ContaLuz],
        mensagem: str = "Contas de luz importadas com sucesso",
        codigo: int = 201,
    ) -> Response:
        payload = [cls.from_entity(entidade).model_dump() for entidade in entidades]
        return Response.sucesso(data=payload, message=mensagem, code=codigo)

