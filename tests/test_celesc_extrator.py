import pandas as pd
from typing import Iterable, Optional, List

from core.dataframe.celesc_extrator import CelescExtrator, TabelaPdfExtratora


class FakeWrapperCelesc(TabelaPdfExtratora):
    def __init__(self, tabelas: List[pd.DataFrame], alvo_index: int = 0) -> None:
        self._tabelas = tabelas
        self._alvo = tabelas[alvo_index]

    def carregar_tabelas_pdf(self, file_path: Optional[str] = None) -> List[pd.DataFrame]:
        return self._tabelas

    def localizar_tabela_com_palavras_chave(
        self,
        tabelas: Iterable[pd.DataFrame],
        palavras_chave: Iterable[str],
        *,
        normalizar: bool = True,
        exigir_todas: bool = True,
    ) -> Optional[pd.DataFrame]:
        return self._alvo


def _raw_tabela_celesc() -> pd.DataFrame:
    # Simula saída bruta do Tabula
    return pd.DataFrame(
        [
            ["irrelevante", "x", "y", "z"],
            [
                "Data Documento Número Referência",
                "Vencimento",
                "Total a Pagar (R$)",
                "Outro",
            ],
            [
                "01/09/2025 1234-5 999 888",
                "10/09/2025",
                "R$ 123,45",
                "",
            ],
            [
                "01/08/2025 2234-5 111 222",
                "10/08/2025",
                "R$ 100,00",
                "",
            ],
        ]
    )


def test_celesc_extrator_fluxo_basico_normaliza_colunas():
    tabela_bruta = _raw_tabela_celesc()
    wrapper = FakeWrapperCelesc([tabela_bruta])
    extrator = CelescExtrator(caminho_pdf="/fake/path.pdf", wrapper=wrapper)
    df = extrator.tabela_final

    # Colunas normalizadas presentes
    for coluna in [
        "Data",
        "Documento",
        "Número-Referência e Unidade-Consumidora",
        "Referência",
        "Vencimento",
        "Valor Total",
    ]:
        assert coluna in df.columns

    # Linhas esperadas (duas)
    assert len(df) == 2
    # Valor Total limpo sem o prefixo R$
    assert df.loc[0, "Valor Total"] == "123,45"
    assert df.loc[1, "Valor Total"] == "100,00"
