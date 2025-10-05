from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional, Iterable, List, Protocol, cast
from collections.abc import Hashable
import pandas as pd
from dataframe_wrapper import DataFrameWrapper


# "Linguagem ubíqua" do domínio SAMAE e princípios SOLID
# - Introduzimos um protocolo (porta) para extração de tabelas de PDF, permitindo inversão de dependência (DIP)
# - Mantemos DataFrameWrapper como implementação padrão dessa porta
class TabelaPdfExtratora(Protocol):
    def carregar_tabelas_pdf(self, file_path: Optional[str] = None) -> List[pd.DataFrame]:
        ...

    def localizar_tabela_com_palavras_chave(
        self,
        tabelas: Iterable[pd.DataFrame],
        palavras_chave: Iterable[str],
        *,
        normalizar: bool = True,
        exigir_todas: bool = True,
    ) -> Optional[pd.DataFrame]:
        ...


PALAVRAS_CHAVE_HISTORICO_CONSUMO = ("HISTÓRICO", "CONSUMO", "VALOR")
PADRAO_MOEDA = r"\d{1,3}(?:\.\d{3})*,\d{2}"
PADRAO_REFERENCIA_MM_YYYY = r"(\b\d{2}/\d{4}\b)"


@dataclass(init=False)
class SamaeExtrator:
    """
    Extrator de Valor Atual em faturas do SAMAE.

    Contrato (entrada/saída):
    - Entrada: caminho do PDF (caminho_pdf) e parâmetros de leitura de tabelas.
    - Saída: DataFrame com colunas ["Referência", "Valor (R$)"] contendo a linha "(Atual)".

    Princípios aplicados:
    - SRP: métodos privados focados em ações pequenas e coesas (detectar coluna, selecionar linha, extrair valor)
    - OCP: heurísticas organizadas para facilitar extensão sem modificar fluxo principal
    - DIP: depende de uma "porta" (TabelaPdfExtratora); DataFrameWrapper é apenas a implementação padrão
    """

    wrapper: TabelaPdfExtratora
    tabela: pd.DataFrame

    def __init__(
        self,
        caminho_pdf: str,
        pages: str = "all",
        multiple_tables: bool = True,
        stream: bool = True,
        lattice: bool = False,
        *,
        wrapper: Optional[TabelaPdfExtratora] = None,
    ) -> None:
        self._caminho_pdf = caminho_pdf
        self.wrapper = wrapper or DataFrameWrapper(
            file_path=caminho_pdf,
            pages=pages,
            multiple_tables=multiple_tables,
            stream=stream,
            lattice=lattice,
        )
        self.tabela = self._extrair_valor_atual()

    # --- Fluxo principal ---------------------------------------------------
    def _extrair_valor_atual(self, file_path: Optional[str] = None) -> pd.DataFrame:
        tabelas = self.wrapper.carregar_tabelas_pdf(file_path or self._caminho_pdf)

        tabela_hist = self.wrapper.localizar_tabela_com_palavras_chave(
            tabelas, PALAVRAS_CHAVE_HISTORICO_CONSUMO, normalizar=True, exigir_todas=False
        )
        if tabela_hist is None:
            # Fallback: escolhe a primeira tabela que tenha uma coluna de valor plausível
            tabela_hist = next((t for t in tabelas if self._detectar_coluna_valor(t) is not None), None)
        if tabela_hist is None:
            raise ValueError("Tabela de consumo/valor não encontrada no PDF.")

        return self._montar_linha_atual(tabela_hist)

    # --- Passos do domínio -------------------------------------------------
    def _montar_linha_atual(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.dropna(axis=1, how="all").reset_index(drop=True)

        valor_col_opt = self._detectar_coluna_valor(df)
        if valor_col_opt is None:
            raise ValueError("Coluna 'Valor (R$)' não encontrada.")
        valor_col: Hashable = valor_col_opt

        linha_atual: pd.Series = self._selecionar_linha_atual(df)

        referencia = self._extrair_referencia(linha_atual)
        valor = self._extrair_valor(linha_atual, valor_col)

        return pd.DataFrame({"Referência": [referencia], "Valor (R$)": [valor]})

    # --- Heurísticas/coadjuvantes -----------------------------------------
    def _detectar_coluna_valor(self, df: pd.DataFrame) -> Optional[Hashable]:
        """Tenta encontrar a coluna de valor pelo cabeçalho e, em fallback, pelo conteúdo."""
        for c in df.columns:
            key = self._chave_normalizada(str(c))
            if key in ("valorrs", "valorr", "valor") or ("valor" in key and ("rs" in key or "r" in key)):
                return c
        # Conteúdo da última coluna como fallback
        ultima: Hashable = cast(Hashable, df.columns[-1])
        amostra = df[ultima].astype(str).str.contains(PADRAO_MOEDA, regex=True, na=False).mean()
        if amostra > 0.3:
            return ultima
        return None

    def _selecionar_linha_atual(self, df: pd.DataFrame) -> pd.Series:
        """Seleciona a linha marcada como (Atual) ou, em falta, a mais recente por mm/yyyy."""
        primeira_col: Hashable = cast(Hashable, df.columns[0])
        primeira_serie: pd.Series = df[primeira_col].astype(str).fillna("")

        # Filtra explícito "(Atual)"
        normalizada: pd.Series = self._sem_acentos_minusculo(primeira_serie)
        mask_atual = normalizada.str.contains(r"\(atual\)", na=False)
        candidatos = df[mask_atual]
        if not candidatos.empty:
            return candidatos.iloc[0]

        # Senão, escolhe por maior mm/yyyy
        mm_yyyy = primeira_serie.apply(self._extrair_mm_yyyy)
        # Converte para ordenação YYYYMM
        ordem_num = mm_yyyy.apply(self._yyyy_mm_int)
        if ordem_num.isna().all():
            raise ValueError("Não foi possível determinar a referência atual.")
        idx_max = ordem_num.idxmax()
        return df.loc[idx_max]

    def _extrair_referencia(self, linha: pd.Series) -> str:
        texto = str(linha.iloc[0])
        m = re.search(PADRAO_REFERENCIA_MM_YYYY, texto)
        if not m:
            raise ValueError("Referência (mm/yyyy) não identificada na linha atual.")
        return f"{m.group(1)} (Atual)"

    def _extrair_valor(self, linha: pd.Series, valor_col: Hashable) -> str:
        valor = str(linha[valor_col]).strip()
        if not valor or valor.lower() == "nan":
            linha_txt = " ".join(linha.astype(str).tolist())
            m_val = re.search(PADRAO_MOEDA, linha_txt)
            if not m_val:
                raise ValueError("Valor atual não identificado.")
            valor = m_val.group(0)
        return valor

    @staticmethod
    def _extrair_mm_yyyy(texto: str) -> Optional[str]:
        if not texto:
            return None
        m = re.search(PADRAO_REFERENCIA_MM_YYYY, texto)
        return m.group(1) if m else None

    @staticmethod
    def _yyyy_mm_int(mm_yyyy: Optional[str]) -> Optional[int]:
        if not mm_yyyy:
            return None
        try:
            mm, yyyy = mm_yyyy.split("/")
            return int(yyyy) * 100 + int(mm)
        except Exception:
            return None

    @staticmethod
    def _sem_acentos_minusculo(serie: pd.Series) -> pd.Series:
        import unicodedata
        def norm_one(s: str) -> str:
            s = unicodedata.normalize("NFKD", s)
            s = "".join(ch for ch in s if not unicodedata.combining(ch))
            return s.lower()
        return serie.astype(str).fillna("").map(norm_one)

    @staticmethod
    def _chave_normalizada(s: str) -> str:
        import unicodedata as _uni
        s = _uni.normalize("NFKD", s)
        s = "".join(ch for ch in s if not _uni.combining(ch)).lower()
        return re.sub(r"[^a-z0-9]", "", s)


def obter_tabela_samae(caminho_pdf: str) -> pd.DataFrame:
    """API pública: retorna DataFrame com 'Referência' e 'Valor (R$)' da linha atual."""
    return SamaeExtrator(caminho_pdf).tabela


if __name__ == "__main__":
    try:
        pdf_agua = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "assets", "samae", "segunda-via.pdf")
        )
        df = obter_tabela_samae(pdf_agua)
        print(df)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Erro: {e}")
