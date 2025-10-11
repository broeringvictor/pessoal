import pandas as pd

from core.dataframe.dataframe_wrapper import DataFrameWrapper


def test_localizar_tabela_com_palavras_chave_all_required_with_normalization():
    # Tabelas simuladas
    df1 = pd.DataFrame({"A": ["foo"], "B": ["bar"]})
    df2 = pd.DataFrame(
        {
            "col": [
                "abc",
                "Referência consumo VALOR",  # contém acentos e variação de caixa
                "xyz",
            ]
        }
    )

    wrapper = DataFrameWrapper()
    encontrada = wrapper.localizar_tabela_com_palavras_chave(
        [df1, df2],
        palavras_chave=["referencia", "valor"],
        normalizar=True,
        exigir_todas=True,
    )
    assert encontrada is df2


def test_localizar_tabela_com_palavras_chave_any_match():
    df = pd.DataFrame({"col": ["apenas referencia aqui"]})
    wrapper = DataFrameWrapper()
    encontrada = wrapper.localizar_tabela_com_palavras_chave(
        [df],
        palavras_chave=["valor", "referencia"],
        normalizar=True,
        exigir_todas=False,
    )
    assert encontrada is df
