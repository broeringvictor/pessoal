from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional, Iterable, List, Protocol, cast
from collections.abc import Hashable
import pandas as pd
from .dataframe_wrapper import DataFrameWrapper


class TabelaPdfExtratora(Protocol):
    def carregar_tabelas_pdf(
        self, file_path: Optional[str] = None
    ) -> List[pd.DataFrame]: ...

    def localizar_tabela_com_palavras_chave(
        self,
        tabelas: Iterable[pd.DataFrame],
        palavras_chave: Iterable[str],
        *,
        normalizar: bool = True,
        exigir_todas: bool = True,
    ) -> Optional[pd.DataFrame]: ...


PALAVRAS_CHAVE_HISTORICO_CONSUMO = ("HISTÓRICO", "CONSUMO", "VALOR")
PADRAO_MOEDA = r"\d{1,3}(?:\.\d{3})*,\d{2}"
PADRAO_REFERENCIA_MM_YYYY = r"(\b\d{2}/\d{4}\b)"


@dataclass(init=False)
class SamaeExtrator:
    """Extrai a linha atual de faturas SAMAE e retorna Referência e Valor (R$)."""

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
            tabelas,
            PALAVRAS_CHAVE_HISTORICO_CONSUMO,
            normalizar=True,
            exigir_todas=False,
        )
        if tabela_hist is None:
            # Fallback: escolhe a primeira tabela que tenha uma coluna de valor plausível
            tabela_hist = next(
                (t for t in tabelas if self._detectar_coluna_valor(t) is not None), None
            )
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
        for coluna_rotulo in df.columns:
            rotulo_normalizado = self._chave_normalizada(str(coluna_rotulo))
            if rotulo_normalizado in ("valorrs", "valorr", "valor") or (
                "valor" in rotulo_normalizado
                and ("rs" in rotulo_normalizado or "r" in rotulo_normalizado)
            ):
                return coluna_rotulo
        # Conteúdo da última coluna como fallback
        ultima_coluna: Hashable = cast(Hashable, df.columns[-1])
        proporcao_padrao_moeda = (
            df[ultima_coluna]
            .astype(str)
            .str.contains(PADRAO_MOEDA, regex=True, na=False)
            .mean()
        )
        if proporcao_padrao_moeda > 0.3:
            return ultima_coluna
        return None

    def _selecionar_linha_atual(self, df: pd.DataFrame) -> pd.Series:
        """Seleciona a linha marcada como (Atual) ou, em falta, a mais recente por mm/yyyy."""
        primeira_coluna: Hashable = cast(Hashable, df.columns[0])
        primeira_serie: pd.Series = df[primeira_coluna].astype(str).fillna("")

        # Filtra explícito "(Atual)"
        texto_normalizado: pd.Series = self._sem_acentos_minusculo(primeira_serie)
        mascara_atual = texto_normalizado.str.contains(r"\(atual\)", na=False)
        linhas_candidatas = df[mascara_atual]
        if not linhas_candidatas.empty:
            return linhas_candidatas.iloc[0]

        # Senão, escolhe por maior mm/yyyy
        serie_mm_yyyy = primeira_serie.apply(self._extrair_mm_yyyy)
        # Converte para ordenação YYYYMM
        ordem_yyyymm = serie_mm_yyyy.apply(self._yyyy_mm_int)
        if ordem_yyyymm.isna().all():
            raise ValueError("Não foi possível determinar a referência atual.")
        indice_maximo = ordem_yyyymm.idxmax()
        return df.loc[indice_maximo]

    def _extrair_referencia(self, linha: pd.Series) -> str:
        texto_celula_inicial = str(linha.iloc[0])
        match = re.search(PADRAO_REFERENCIA_MM_YYYY, texto_celula_inicial)
        if not match:
            raise ValueError("Referência (mm/yyyy) não identificada na linha atual.")
        return f"{match.group(1)} (Atual)"

    def _extrair_valor(self, linha: pd.Series, valor_col: Hashable) -> str:
        valor_str = str(linha[valor_col]).strip()
        if not valor_str or valor_str.lower() == "nan":
            linha_texto = " ".join(linha.astype(str).tolist())
            match_valor = re.search(PADRAO_MOEDA, linha_texto)
            if not match_valor:
                raise ValueError("Valor atual não identificado.")
            valor_str = match_valor.group(0)
        return valor_str

    @staticmethod
    def _extrair_mm_yyyy(texto: str) -> Optional[str]:
        if not texto:
            return None
        match = re.search(PADRAO_REFERENCIA_MM_YYYY, texto)
        return match.group(1) if match else None

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
        import unicodedata as _unicodedata

        def normalizar_texto(texto: str) -> str:
            texto_norm = _unicodedata.normalize("NFKD", texto)
            texto_sem_acentos = "".join(
                caractere
                for caractere in texto_norm
                if not _unicodedata.combining(caractere)
            )
            return texto_sem_acentos.lower()

        return serie.astype(str).fillna("").map(normalizar_texto)

    @staticmethod
    def _chave_normalizada(texto: str) -> str:
        import unicodedata as _unicodedata

        texto_norm = _unicodedata.normalize("NFKD", texto)
        texto_sem_acentos = "".join(
            caractere
            for caractere in texto_norm
            if not _unicodedata.combining(caractere)
        ).lower()
        return re.sub(r"[^a-z0-9]", "", texto_sem_acentos)


def obter_tabela_samae(caminho_pdf: str) -> pd.DataFrame:
    """API pública: retorna DataFrame com 'Referência' e 'Valor (R$)' da linha atual."""
    return SamaeExtrator(caminho_pdf).tabela


if __name__ == "__main__":
    try:
        pdf_agua = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__), "..", "assets", "samae", "segunda-via.pdf"
            )
        )
        df = obter_tabela_samae(pdf_agua)
        print(df)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Erro: {e}")
