from __future__ import annotations
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import UploadFile
from pydantic import BaseModel, Field
from application.conta_agua.response import ContaAguaOut

class ImportarContaAguaCommand(BaseModel):
    """Schema de entrada para importar uma ContaAgua a partir de um arquivo PDF."""
    arquivo_pdf: UploadFile = Field(..., description="Arquivo PDF contendo a conta de água.")

class AtualizarContaAguaCommand(BaseModel):
    """Schema de entrada para atualizar parcialmente uma ContaAgua existente."""
    conta_agua_id: UUID
    mes_referencia: Optional[str] = Field(
        None, description="Novo mes/ano da referencia (opcional)."
    )
    valor: Optional[Decimal | str] = Field(
        None, description="Novo valor monetario (opcional)."
    )
class PutContaAguaCommand(BaseModel):
    """Schema (input) para a operacao de upsert de ContaAgua.
    - Envie `conta_agua_id` para atualizar uma existente.
    - Omitir `conta_agua_id` para criar uma nova.
    """
    conta_agua_id: Optional[UUID] = Field(
        None, description="Identificador da conta (opcional para criar)."
    )
    mes_referencia: str = Field(
        ..., description="Mes/ano no formato mm/aaaa ou texto equivalente."
    )
    valor: Decimal | str = Field(
        ..., description="Valor monetario da conta; aceita Decimal ou string formatada."
    )
class PutContaAguaResult(BaseModel):
    """Schema (output) padronizado para a operacao de upsert de ContaAgua."""
    conta_agua: ContaAguaOut
