from decimal import Decimal
import pytest

from core.shared.value_objects import ReferenciaMensal, ValorMonetario


def test_referencia_mensal_normaliza_e_valida():
    ref = ReferenciaMensal(" 09/2025 (Atual) ")
    assert ref.referencia == "09/2025"
    assert ref.as_tuple() == (9, 2025)

    with pytest.raises(ValueError):
        ReferenciaMensal("2025-09")

    with pytest.raises(ValueError):
        ReferenciaMensal("13/2025")


def test_valor_monetario_from_bruto_e_centavos():
    v1 = ValorMonetario.from_bruto("R$ 1.234,56")
    assert v1.valor == Decimal("1234.56")
    assert v1.to_centavos() == 123456

    v2 = ValorMonetario.from_centavos(987)
    assert v2.valor == Decimal("9.87")
    assert v2.to_centavos() == 987

    with pytest.raises(ValueError):
        ValorMonetario.from_bruto("abc")
