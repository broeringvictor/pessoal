from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel

from application.shared.response import Response
from core.entities.conta_agua import ContaAgua


class ContaAguaOut(Response):
    referencia: str
    valor: Decimal

    @classmethod
    def from_entity(cls, entidade: ContaAgua) -> "ContaAguaOut":
        return cls(referencia=entidade.referencia, valor=entidade.valor)

    @classmethod
    def response_importacao(
        cls,
        entidades: list[ContaAgua],
        mensagem: str = "Contas de água importadas com sucesso",
        codigo: int = 201,
    ) -> Response:
        payload = [cls.from_entity(entidade).model_dump() for entidade in entidades]
        return Response.sucesso(data=payload, message=mensagem, code=codigo)

    @classmethod
    def sucesso_de_entidade(
        cls,
        entidade: ContaAgua,
        mensagem: str = "Conta de água obtida com sucesso",
        codigo: int = 200,
    ) -> Response:
        # Empacota o DTO em Response.sucesso
        return Response.sucesso(data=cls.from_entity(entidade).model_dump(), message=mensagem, code=codigo)

    @classmethod
    def sucesso_de_lista(
        cls,
        entidades: list[ContaAgua],
        mensagem: str = "Contas de água obtidas com sucesso",
        codigo: int = 200,
    ) -> Response:
        payload = [cls.from_entity(entidade).model_dump() for entidade in entidades]
        return Response.sucesso(data=payload, message=mensagem, code=codigo)

    @classmethod
    def criado_de_entidade(
        cls,
        entidade: ContaAgua,
        mensagem: str = "Conta de água criada com sucesso",
    ) -> Response:
        return Response.sucesso(data=cls.from_entity(entidade).model_dump(), message=mensagem, code=201)
