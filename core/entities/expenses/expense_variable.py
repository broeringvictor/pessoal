# core/entities/expenses/expense_variable.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Union
from uuid import UUID

from core.entities.expense import Expense
from core.value_object import Description, MonetaryValue, ExpenseType, EventDate
from core.entities.expenses.expense_variable_type import ExpenseVariableType


@dataclass(slots=True, kw_only=True)
class ExpenseVariable(Expense):
    """
    Variable expense entity (e.g., utility bills).

    Domain fields:
    - description: Description (VO)
    - amount: MonetaryValue (VO)
    - expense_type: ExpenseType (VO)
    - event_date: EventDate (VO)
    - expense_variable_type_id: UUID for the variable type (optional)
    """
    event_date: EventDate
    expense_variable_type_id: Optional[UUID] = None

    bill_label: str = "Expense"

    _NOT_PROVIDED: object = object()

    # ----------------- Utilities -----------------
    @staticmethod
    def _extract_type_id(value: Optional[Union[UUID, "ExpenseVariableType"]]) -> Optional[UUID]:
        if isinstance(value, ExpenseVariableType):
            return value.id
        if isinstance(value, UUID):
            return value
        return None

    @staticmethod
    def _coerce_event_date(value: Union[str, date, datetime, EventDate]) -> EventDate:
        if isinstance(value, EventDate):
            return value
        if isinstance(value, (date, datetime)):
            return EventDate.criar_de_data(value)
        return EventDate.criar_de_texto(str(value))

    @staticmethod
    def _coerce_amount(value: Union[str, int, float, Decimal, MonetaryValue]) -> MonetaryValue:
        return value if isinstance(value, MonetaryValue) else MonetaryValue.criar_de_bruto(value)

    @staticmethod
    def _coerce_description(value: Union[str, Description]) -> Description:
        return value if isinstance(value, Description) else Description.criar_de_texto(value)

    @staticmethod
    def _coerce_expense_type(value: Union[ExpenseType, int, str]) -> ExpenseType:
        if isinstance(value, ExpenseType):
            return value
        try:
            return ExpenseType.criar_de_codigo(value)
        except Exception:
            if isinstance(value, str):
                return ExpenseType.criar_de_nome(value)
            raise

    # ----------------- Factory (Create) -----------------
    @classmethod
    def criar(
        cls,
        *,
        description: Union[str, Description],
        amount: Union[str, int, float, Decimal, MonetaryValue],
        expense_type: Union[ExpenseType, int, str],
        event_date: Union[str, date, datetime, EventDate],
        variable_type: Optional[Union[UUID, "ExpenseVariableType"]] = None,
    ) -> "ExpenseVariable":
        desc_vo = cls._coerce_description(description)
        amount_vo = cls._coerce_amount(amount)
        type_vo = cls._coerce_expense_type(expense_type)
        date_vo = cls._coerce_event_date(event_date)
        type_id = cls._extract_type_id(variable_type)
        return cls(
            description=desc_vo,
            amount=amount_vo,
            expense_type=type_vo,
            event_date=date_vo,
            expense_variable_type_id=type_id,
        )

    # ----------------- Full Update -----------------
    def atualizar(
        self,
        *,
        description: Union[str, Description],
        amount: Union[str, int, float, Decimal, MonetaryValue],
        expense_type: Union[ExpenseType, int, str],
        event_date: Union[str, date, datetime, EventDate],
        variable_type: Optional[Union[UUID, "ExpenseVariableType"]] = None,
    ) -> "ExpenseVariable":
        self.description = self._coerce_description(description)
        self.amount = self._coerce_amount(amount)
        self.expense_type = self._coerce_expense_type(expense_type)
        self.event_date = self._coerce_event_date(event_date)
        self.expense_variable_type_id = self._extract_type_id(variable_type)
        self.registrar_atualizacao()
        return self

    # ----------------- Partial Update (Patch) -----------------
    def patch(
        self,
        *,
        description: Optional[Union[str, Description]] = None,
        amount: Optional[Union[str, int, float, Decimal, MonetaryValue]] = None,
        expense_type: Optional[Union[ExpenseType, int, str]] = None,
        event_date: Optional[Union[str, date, datetime, EventDate]] = None,
        variable_type: object = _NOT_PROVIDED,
    ) -> "ExpenseVariable":
        changed = False
        if description is not None:
            self.description = self._coerce_description(description)
            changed = True
        if amount is not None:
            self.amount = self._coerce_amount(amount)
            changed = True
        if expense_type is not None:
            self.expense_type = self._coerce_expense_type(expense_type)
            changed = True
        if event_date is not None:
            self.event_date = self._coerce_event_date(event_date)
            changed = True
        if variable_type is not self._NOT_PROVIDED:
            self.expense_variable_type_id = self._extract_type_id(variable_type)  # type: ignore[arg-type]
            changed = True
        if changed:
            self.registrar_atualizacao()
        return self

    # ----------------- Soft Delete -----------------
    def delete(self) -> None:
        self.register_deletion()

    # ----------------- Presentation helpers -----------------
    @property
    def reference(self) -> str:
        return f"{self.event_date.mes:02d}/{self.event_date.ano}"

    def short_description(self) -> str:
        return f"{self.bill_label} {self.reference}: R$ {self.amount.valor:.2f}"
