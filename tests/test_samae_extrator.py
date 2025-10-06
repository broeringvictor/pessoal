import pandas as pd
from typing import Iterable, Optional, List

from core.dataframe.samae_extrator import SamaeExtrator, TabelaPdfExtratora


class FakeWrapperSamae(TabelaPdfExtratora):
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


def test_samae_extrator_com_atual():
    tabela = pd.DataFrame(
        {
            "Período": ["08/2025", "09/2025 (Atual)"],
            "Valor (R$)": ["39,10", "42,20"],
        }
    )
    wrapper = FakeWrapperSamae([tabela])
    extrator = SamaeExtrator(caminho_pdf="/fake/path.pdf", wrapper=wrapper)
    df = extrator.tabela

    assert list(df.columns) == ["Referência", "Valor (R$)"]
    assert len(df) == 1
    assert df.iloc[0]["Referência"] == "09/2025 (Atual)"
    assert df.iloc[0]["Valor (R$)"] == "42,20"


def test_samae_extrator_sem_atual_pega_mais_recente():
    tabela = pd.DataFrame(
        {
            "Período": ["07/2025", "08/2025", "09/2025"],
            "Valor (R$)": ["38,00", "39,10", "42,20"],
        }
    )
    wrapper = FakeWrapperSamae([tabela])
    extrator = SamaeExtrator(caminho_pdf="/fake/path.pdf", wrapper=wrapper)
    df = extrator.tabela

    assert df.iloc[0]["Referência"] == "09/2025 (Atual)"
    assert df.iloc[0]["Valor (R$)"] == "42,20"
