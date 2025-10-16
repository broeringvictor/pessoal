from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from application.conta_luz.response import ContaLuzOut


class AtualizarContaLuzCommand(BaseModel):
    """Schema de entrada para atualizar parcialmente uma ContaLuz existente."""

    conta_luz_id: UUID
    mes_referencia: Optional[str] = Field(
        None, description="Novo mes/ano da referencia (opcional)."
    )
    valor: Optional[Decimal | str] = Field(
        None, description="Novo valor monetario (opcional)."
    )


class PutContaLuzCommand(BaseModel):
    """Schema (input) para a operacao de upsert de ContaLuz.
    - Envie `conta_luz_id` para atualizar uma existente.
    - Omitir `conta_luz_id` para criar uma nova.
    """

    conta_luz_id: Optional[UUID] = Field(
        None, description="Identificador da conta (opcional para criar)."
    )
    mes_referencia: str = Field(
        ..., description="Mes/ano no formato mm/aaaa ou texto equivalente."
    )
    valor: Decimal | str = Field(
        ..., description="Valor monetario da conta; aceita Decimal ou string formatada."
    )


class PutContaLuzResult(BaseModel):
    """Schema (output) padronizado para a operacao de upsert de ContaLuz."""

    conta_luz: ContaLuzOut

