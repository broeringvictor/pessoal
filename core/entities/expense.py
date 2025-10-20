from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod

from core.shared.entities import Entity
from core.value_object import Description, MonetaryValue, ExpenseType


@dataclass(slots=True, kw_only=True)
class Expense(Entity, ABC):
    """Abstract base entity for the expense hierarchy.

    - Must not be instantiated directly.
    - Fields use strict Value Objects (no coercion here).
    - Subclasses are responsible for factories that convert raw inputs into VOs.
    """

    description: Description
    amount: MonetaryValue
    expense_type: ExpenseType

    # ----------------- Factory (Create) -----------------
    @classmethod
    @abstractmethod
    def criar(
        cls,
        *args,
        **kwargs,
    ) -> "Expense":
        """Subclasses must implement context-specific factories."""
        raise NotImplementedError

    @classmethod
    def create(
        cls,
        *,
        description: Description,
        amount: MonetaryValue,
        expense_type: ExpenseType,
        **kwargs,
    ) -> "Expense":
        """English alias that delegates to criar()."""
        return cls.criar(description=description, amount=amount, expense_type=expense_type, **kwargs)

    # ----------------- Full Update -----------------
    def atualizar(
        self,
        *,
        description: Description,
        amount: MonetaryValue,
        expense_type: ExpenseType,
        **kwargs,
    ) -> "Expense":
        self.description = description
        self.amount = amount
        self.expense_type = expense_type
        self.registrar_atualizacao()
        return self

    def update(
        self,
        *,
        description: Description,
        amount: MonetaryValue,
        expense_type: ExpenseType,
        **kwargs,
    ) -> "Expense":
        """English alias that delegates to atualizar()."""
        return self.atualizar(description=description, amount=amount, expense_type=expense_type, **kwargs)

    # ----------------- Partial Update (Patch) -----------------
    def patch(
        self,
        *,
        description: Optional[Description] = None,
        amount: Optional[MonetaryValue] = None,
        expense_type: Optional[ExpenseType] = None,
    ) -> "Expense":
        changed = False
        if description is not None:
            self.description = description
            changed = True
        if amount is not None:
            self.amount = amount
            changed = True
        if expense_type is not None:
            self.expense_type = expense_type
            changed = True

        if changed:
            self.registrar_atualizacao()
        return self

    # ----------------- Soft Delete -----------------
    def delete(self) -> None:
        self.register_deletion()
