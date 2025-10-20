# core/entities/expenses/expense_variable_type.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Union

# Assumindo que a classe Entity está em core.shared.entities
from core.shared.entities import Entity
from core.value_object import Descricao


@dataclass(slots=True, kw_only=True)
class ExpenseVariableType(Entity):
    """
    Entidade que representa um tipo/categoria de despesa variável.
    Herda de Entity para gerenciamento de ID e timestamps.
    """
    # Atributos específicos desta entidade
    name: str
    description: Optional[Descricao] = None
    is_active: bool = True

    # Sentinel para distinguir "não fornecido" de "fornecido como None" em patch
    _NAO_FORNECIDO: classmethod = object()  # type: ignore[assignment]

    # ----------------- Utilidades internas -----------------
    @staticmethod
    def _coagir_para_descricao(valor: Optional[Union[str, Descricao]]) -> Optional[Descricao]:
        if valor is None:
            return None
        if isinstance(valor, Descricao):
            return valor
        if isinstance(valor, str):
            return Descricao.criar_de_texto(valor)
        raise TypeError("description deve ser str, Descricao ou None.")

    # ----------------- Fábrica (Create) -----------------
    @classmethod
    def criar(
            cls,
            *,
            name: str,
            description: Optional[Union[str, Descricao]] = None,
            is_active: bool = True,
    ) -> "ExpenseVariableType":
        """
        Método de fábrica para criar uma nova instância de tipo de despesa.
        """
        descricao_vo = cls._coagir_para_descricao(description)
        return cls(name=name, description=descricao_vo, is_active=is_active)

    # ----------------- Atualização Completa (Update) -----------------
    def atualizar(
            self,
            *,
            name: str,
            description: Optional[Union[str, Descricao]],
            is_active: bool,
    ) -> "ExpenseVariableType":
        """Atualiza todos os campos da entidade."""
        self.name = name
        self.description = self._coagir_para_descricao(description)
        self.is_active = is_active
        self.registrar_atualizacao()
        return self

    # ----------------- Atualização Parcial (Patch) -----------------
    def patch(
            self,
            *,
            name: Optional[str] = None,
            description: object = _NAO_FORNECIDO,  # permite None explícito
            is_active: Optional[bool] = None,
    ) -> "ExpenseVariableType":
        """Atualiza apenas os campos fornecidos.
        Para a descrição:
        - omitido: mantém
        - None: remove descrição
        - str/Descricao: aplica VO
        """
        houve_mudanca = False
        if name is not None:
            self.name = name
            houve_mudanca = True
        # A descrição pode ser explicitamente definida como None
        if description is not self._NAO_FORNECIDO:
            self.description = self._coagir_para_descricao(description)  # type: ignore[arg-type]
            houve_mudanca = True
        if is_active is not None:
            self.is_active = is_active
            houve_mudanca = True

        if houve_mudanca:
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
            "description": self.description.como_texto() if self.description else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }