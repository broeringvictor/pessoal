import uuid
from decimal import Decimal
from core.entities import ContaLuz


def test_criar_normaliza_referencia_e_valor_e_gera_id():
    conta = ContaLuz.criar("09/2025 (Atual)", "R$ 1.234,56")
    assert conta.referencia == "09/2025"
    assert conta.valor == Decimal("1234.56")
    assert isinstance(conta.id, uuid.UUID)
    assert conta.id.version == 7


def test_atualizar_mantem_normalizacao_e_define_updated_at():
    conta = ContaLuz.criar("08/2025", "100")
    assert conta.updated_at is None
    conta.atualizar(mes_referencia="09/2025 (Atual)", valor="1.000,10")
    assert conta.referencia == "09/2025"
    assert conta.valor == Decimal("1000.10")
    assert conta.updated_at is not None


def test_deletar_define_deleted_at_e_flag():
    conta = ContaLuz.criar("08/2025", 10)
    assert conta.deleted_at is None
    assert not conta.is_deleted
    conta.deletar()
    assert conta.deleted_at is not None
    assert conta.is_deleted


def test_descricao_curta_formata_valor_com_duas_casas():
    conta = ContaLuz.criar("09/2025", "1234.5")
    descricao = conta.descricao_curta()
    assert "Conta de Luz 09/2025: R$ 1234.50" == descricao


def test_referencia_invalida_levanta_erro():
    try:
        ContaLuz.criar("2025-09", 10)
        raise AssertionError("Esperava ValueError para referência inválida")
    except ValueError:
        pass


def test_valor_invalido_levanta_erro():
    try:
        ContaLuz.criar("09/2025", "abc")
        raise AssertionError("Esperava ValueError para valor inválido")
    except ValueError:
        pass

