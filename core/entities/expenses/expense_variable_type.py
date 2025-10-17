# core/entities/expenses/expense_variable_type.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# Assumindo que a classe Entity está em core.shared.entities
from core.shared.entities import Entity

@dataclass(slots=True)
class ExpenseVariableType(Entity):
    """
    Entidade que representa um tipo/categoria de despesa variável.
    Herda de Entity para gerenciamento de ID e timestamps.
    """
    # Atributos específicos desta entidade
    name: str
    description: Optional[str] = None
    is_active: bool = True

    # ----------------- Fábrica (Create) -----------------
    @classmethod
    def criar(
            cls,
            *,
            name: str,
            description: Optional[str] = None,
            is_active: bool = True,
    ) -> "ExpenseVariableType":
        """Método de fábrica para criar uma nova instância de tipo de despesa."""
        return cls(name=name, description=description, is_active=is_active)

    # ----------------- Atualização Completa (Update) -----------------
    def atualizar(
            self,
            *,
            name: str,
            description: Optional[str],
            is_active: bool,
    ) -> "ExpenseVariableType":
        """Atualiza todos os campos da entidade."""
        self.name = name
        self.description = description
        self.is_active = is_active
        self.registrar_atualizacao()
        return self

    # ----------------- Atualização Parcial (Patch) -----------------
    def patch(
            self,
            *,
            name: Optional[str] = None,
            description: Optional[Optional[str]] = None,
            is_active: Optional[bool] = None,
    ) -> "ExpenseVariableType":
        """Atualiza apenas os campos fornecidos."""
        if name is not None:
            self.name = name
        # A descrição pode ser explicitamente definida como None
        if description is not None:
            self.description = description
        if is_active is not None:
            self.is_active = is_active

        # Apenas registra atualização se algo mudou
        if any((name, description, is_active)):
            self.registrar_atualizacao()

        return self

    # ----------------- Exclusão Lógica (Soft Delete) -----------------
    def deletar(self) -> None:
        """Realiza a exclusão lógica da entidade."""
        self.is_active = False
        self.registrar_exclusao()

    # ----------------- Conversão para Dicionário -----------------
    def to_dict(self) -> dict:
        """Converte a entidade para um dicionário, útil para serialização (ex: JSON)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }