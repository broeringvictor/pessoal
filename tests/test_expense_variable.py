from datetime import datetime

from core.entities.expenses.expense_variable import ExpenseVariable


def test_expense_variable_updates_updated_at_on_changes():
    # Cria uma despesa variável
    despesa = ExpenseVariable.criar(
        mes_referencia="09/2025",
        valor=100,  # aceita int/float/str/Decimal ou VO Valor
    )

    # Ao criar, updated_at deve ser None
    assert despesa.updated_at is None

    # Patch com alteração deve registrar atualização
    despesa.patch(valor=200)
    assert despesa.updated_at is not None
    atualizado_apos_patch = despesa.updated_at

    # Patch sem alteração não deve mudar updated_at
    despesa.patch()
    assert despesa.updated_at == atualizado_apos_patch

    # Update completo deve atualizar novamente
    despesa.atualizar(mes_referencia="10/2025", valor=300)
    assert despesa.updated_at is not None
    assert despesa.updated_at >= atualizado_apos_patch

