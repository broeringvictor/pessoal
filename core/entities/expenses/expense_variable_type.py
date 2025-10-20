from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Union
from core.shared.entities import Entity
from core.value_object import Description


@dataclass(slots=True, kw_only=True)
class ExpenseVariableType(Entity):
    """
    Entity representing a variable expense category/type.
    Inherits from Entity for ID and timestamps management.
    """
    # Specific attributes of this entity
    name: str
    description: Optional[Description] = None
    is_active: bool = True

    # Sentinel to distinguish not-provided from explicit None in patch
    _NOT_PROVIDED: object = object()

    @staticmethod
    def _coerce_description(value: object) -> Optional[Description]:
        if value is None:
            return None
        if isinstance(value, Description):
            return value
        if isinstance(value, str):
            return Description.criar_de_texto(value)
        raise TypeError("description must be str, Description or None.")

    # ----------------- Factory (Create) -----------------
    @classmethod
    def criar(
        cls,
        *,
        name: str,
        description: Optional[Union[str, Description]] = None,
        is_active: bool = True,
    ) -> "ExpenseVariableType":
        """Factory method to create a new variable expense type instance."""
        description_vo = cls._coerce_description(description)
        return cls(name=name, description=description_vo, is_active=is_active)

    # ----------------- Full Update -----------------
    def atualizar(
        self,
        *,
        name: str,
        description: Optional[Union[str, Description]],
        is_active: bool,
    ) -> "ExpenseVariableType":
        """Updates all fields of the entity."""
        self.name = name
        self.description = self._coerce_description(description)
        self.is_active = is_active
        self.registrar_atualizacao()
        return self

    # ----------------- Partial Update (Patch) -----------------
    def patch(
        self,
        *,
        name: Optional[str] = None,
        description: object = _NOT_PROVIDED,  # allows explicit None
        is_active: Optional[bool] = None,
    ) -> "ExpenseVariableType":
        """Updates only the provided fields.
        For description:
        - omitted: keep
        - None: remove description
        - str/Description: apply VO
        """
        changed = False
        if name is not None:
            self.name = name
            changed = True
        if description is not self._NOT_PROVIDED:
            self.description = self._coerce_description(description)
            changed = True
        if is_active is not None:
            self.is_active = is_active
            changed = True

        if changed:
            self.registrar_atualizacao()

        return self

    # ----------------- Soft Delete -----------------
    def delete(self) -> None:
        """Performs soft deletion of the entity."""
        self.is_active = False
        self.registrar_exclusao()

    # ----------------- Serialization -----------------
    def to_dict(self) -> dict:
        """Converts the entity to a serializable dict (e.g., JSON)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description.como_texto() if self.description else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }