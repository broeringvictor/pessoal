from core.entities.expenses.expense_variable import ExpenseVariable


def test_expense_variable_updates_updated_at_on_changes():
    # Create a variable expense using VO factories under the hood
    expense = ExpenseVariable.criar(
        description="Power Bill",
        amount=100,  # raw is converted to MonetaryValue VO
        expense_type=1,  # accepts code, name, or ExpenseType VO
        event_date="01/09/2025",  # EventDate (DD/MM/YYYY)
    )

    # On create, updated_at should be None
    assert expense.updated_at is None

    # Patch with change should register update
    expense.patch(amount=200)
    assert expense.updated_at is not None
    updated_after_patch = expense.updated_at

    # Patch without changes should not move updated_at
    expense.patch()
    assert expense.updated_at == updated_after_patch

    # Full update should update again
    expense.atualizar(
        description="Power Bill Updated",
        amount=300,
        expense_type="FIXA",
        event_date="01/10/2025",
    )
    assert expense.updated_at is not None
    assert expense.updated_at >= updated_after_patch
