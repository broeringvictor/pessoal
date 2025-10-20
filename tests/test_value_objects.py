from decimal import Decimal
import pytest
from datetime import date, datetime

from core.shared.value_objects import ReferenciaMensal, ValorMonetario
from core.shared.value_objects.normalizar_data import NormalizarData
from core.value_object.evento_data import EventoData
from core.entradas.entrada_entidade import Entrada


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


@pytest.mark.parametrize(
    "texto, esperado_br, esperado_iso",
    [
        ("1/9/2025", "01/09/2025", "2025-09-01"),
        (" 01/09/2025 ", "01/09/2025", "2025-09-01"),
        ("29/02/2024", "29/02/2024", "2024-02-29"),  # ano bissexto
    ],
)
def test_normalizar_data_normaliza_e_exporta_para_postgres(texto, esperado_br, esperado_iso):
    data_normalizada = NormalizarData(texto)
    assert data_normalizada.data == esperado_br
    assert data_normalizada.as_postgres_value() == esperado_iso
    assert data_normalizada.as_tuple() == (
        int(esperado_br[:2]),
        int(esperado_br[3:5]),
        int(esperado_br[6:10]),
    )
    assert data_normalizada.as_date() == date.fromisoformat(esperado_iso)


@pytest.mark.parametrize(
    "texto_invalido",
    [
        "2025-09-01",   # formato ISO inválido para entrada
        "31/02/2021",   # dia inexistente
        "32/01/2020",   # dia inválido
        "00/12/2020",   # dia zero
        "12/13/2020",   # mês inválido
        "abc",          # texto sem data
        "1/1/20",       # ano com 2 dígitos
        "29/02/2021",   # não é bissexto
    ],
)
def test_normalizar_data_rejeita_entradas_invalidas(texto_invalido):
    with pytest.raises(ValueError):
        NormalizarData(texto_invalido)


def test_data_entrada_criacao_e_persistencia():
    entrada = EventoData.criar_de_texto(" 1/9/2025 ")
    assert entrada.como_texto() == "01/09/2025"
    assert entrada.como_iso() == "2025-09-01"
    assert entrada.para_banco() == date(2025, 9, 1)
    assert entrada.esta_normalizada() is True

    entrada_atualizada = entrada.atualizar_data("02/10/2025")
    assert entrada_atualizada.como_texto() == "02/10/2025"
    assert entrada_atualizada.como_iso() == "2025-10-02"
    assert entrada_atualizada.para_banco() == date(2025, 10, 2)


def test_data_entrada_criacao_de_datetime():
    entrada = EventoData.criar_de_data(datetime(2024, 2, 29, 12, 30))
    assert entrada.como_texto() == "29/02/2024"
    assert entrada.como_iso() == "2024-02-29"
    assert entrada.para_banco() == date(2024, 2, 29)


@pytest.mark.parametrize(
    "texto_invalido",
    [
        "31/02/2021",
        "2025-09-01",
        "1/1/20",
        "abc",
    ],
)
def test_data_entrada_rejeita_entradas_invalidas(texto_invalido):
    with pytest.raises(ValueError):
        EventoData.criar_de_texto(texto_invalido)


def test_entrada_criacao_e_mapeamento_para_banco():
    entrada = Entrada.criar_nova(
        descricao_transacao="Salário Setembro",
        texto_data_evento="01/09/2025",
        texto_mes_referencia="09/2025",
        valor_monetario=ValorMonetario.from_centavos(123456),
    )

    assert isinstance(entrada.data_evento, EventoData)
    assert entrada.data_evento.como_texto() == "01/09/2025"
    assert isinstance(entrada.mes_referencia, ReferenciaMensal)
    assert entrada.mes_referencia.referencia == "09/2025"

    registro = entrada.como_registro_banco()
    assert "id" in registro and registro["id"] is not None
    assert registro["descricao_transacao"] == "Salário Setembro"
    assert registro["data_evento"] == date(2025, 9, 1)
    assert registro["mes_referencia"] == date(2025, 9, 1)
    assert registro["valor_monetario_centavos"] == 123456
    assert registro["created_at"] is not None
    assert "updated_at" in registro  # pode ser None até a primeira atualização


def test_entrada_mutacoes_atualizam_updated_at():
    entrada = Entrada.criar_nova(
        descricao_transacao="Venda",
        texto_data_evento="02/10/2025",
        texto_mes_referencia="10/2025",
        valor_monetario=None,
    )
    assert entrada.updated_at is None

    entrada.alterar_descricao_transacao("Venda Ajustada")
    assert entrada.descricao_transacao == "Venda Ajustada"
    assert entrada.updated_at is not None

    atualizado_apos_primeira = entrada.updated_at
    entrada.alterar_data_evento("03/10/2025")
    assert entrada.data_evento.como_texto() == "03/10/2025"
    assert entrada.updated_at >= atualizado_apos_primeira

    atualizado_apos_segunda = entrada.updated_at
    entrada.alterar_mes_referencia("11/2025")
    assert entrada.mes_referencia.referencia == "11/2025"
    assert entrada.updated_at >= atualizado_apos_segunda

