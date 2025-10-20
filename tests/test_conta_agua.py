import uuid
from decimal import Decimal
from datetime import date
from core.entities import ContaAgua


def test_criar_normaliza_referencia_e_valor_e_gera_id():
    conta = ContaAgua.criar("09/2025 (Atual)", "R$ 1.234,56")
    assert conta.referencia == "09/2025"
    assert conta.valor == Decimal("1234.56")
    assert isinstance(conta.id, uuid.UUID)
    assert conta.id.version == 7


def test_atualizar_mantem_normalizacao_e_define_updated_at():
    conta = ContaAgua.criar("08/2025", "100")
    assert conta.updated_at is None
    conta.atualizar(mes_referencia="09/2025 (Atual)", valor="1.000,10")
    assert conta.referencia == "09/2025"
    assert conta.valor == Decimal("1000.10")
    assert conta.updated_at is not None


def test_deletar_define_deleted_at_e_flag():
    conta = ContaAgua.criar("08/2025", 10)
    assert conta.deleted_at is None
    assert not conta.is_deleted
    conta.delete()
    assert conta.deleted_at is not None
    assert conta.is_deleted


def test_descricoes_e_formatos_para_banco():
    conta = ContaAgua.criar("09/2025", "1234.5")
    assert conta.descricao_curta() == "Conta de Água 09/2025: R$ 1234.50"
    assert conta.referencia_para_banco() == date(2025, 9, 1)
